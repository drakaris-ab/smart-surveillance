/**
 * CameraCanvas
 *
 * Renders one camera by drawing the analysed frame and the boxes measured from
 * that same frame onto a single canvas.
 *
 * Why not an <img> MJPEG stream with a canvas layered over it -- the obvious
 * approach, and the one this replaces: a browser will not tell a page which
 * frame of a multipart stream is currently on screen. There is no event, no
 * metadata, nothing. So boxes fetched by a separate poll are always from a
 * different moment than the pixels underneath them, and every object appears
 * displaced in its direction of travel by however far it moved in the interval.
 * Standing still it looks perfect; walking it looks like a broken detector. That
 * apparent inaccuracy is a rendering artefact, not a detection error, and no
 * amount of detector tuning removes it.
 *
 * The worker therefore hands over the JPEG and its boxes as one object, and this
 * component draws both in the same pass. Boxes cannot be stale here because they
 * arrived with their own pixels.
 *
 * Deliberately no interpolation between updates. Smoothing box positions towards
 * a predicted future would reintroduce exactly the mismatch this design removes:
 * the box would move while its pixels did not.
 */

import React, { useCallback, useEffect, useRef, useState } from "react";

const IDLE_RETRY_MS = 1000;

// Threat state first -- if an object is a confirmed threat, that is the only
// thing about it worth colouring for.
function colourFor(object) {
  if (object.is_threat) {
    return object.severity_rank >= 3 ? "#dc2626" : "#f97316";
  }
  if (object.is_person) return "#38bdf8";
  if (object.ownerless) return "#facc15";
  if (object.is_candidate) return "#22c55e";
  return "#94a3b8";
}

function labelFor(object) {
  const name = object.class_name || "object";
  const id = object.track_id != null ? ` #${object.track_id}` : "";
  if (object.is_threat) return `${name}${id} · ${object.duration || 0}s`;
  if (object.ownerless && object.dwell_seconds) {
    return `${name}${id} · unattended ${Math.round(object.dwell_seconds)}s`;
  }
  return `${name}${id}`;
}

function drawFrame(canvas, image, payload) {
  // The streamed JPEG may be downscaled by the worker while boxes stay in
  // analysis-frame pixels, so everything is scaled by the ratio between the two
  // rather than assuming they match. Drawing boxes onto the same canvas as the
  // image means the browser's own layout scaling applies to both equally: no
  // separate overlay to keep in step, and no dependence on the tile's size.
  const width = image.naturalWidth || payload.frame_width || 0;
  const height = image.naturalHeight || payload.frame_height || 0;
  if (!width || !height) return;

  if (canvas.width !== width || canvas.height !== height) {
    canvas.width = width;
    canvas.height = height;
  }

  const context = canvas.getContext("2d");
  context.drawImage(image, 0, 0, width, height);

  const scale = payload.frame_width ? width / payload.frame_width : 1;
  const stroke = Math.max(2, Math.round(width / 480));
  const fontSize = Math.max(11, Math.round(width / 60));
  context.lineJoin = "round";
  context.font = `600 ${fontSize}px system-ui, sans-serif`;
  context.textBaseline = "top";

  (payload.objects || []).forEach((object) => {
    const box = object.bbox;
    if (!box || box.length < 4) return;
    const x1 = box[0] * scale;
    const y1 = box[1] * scale;
    const boxWidth = (box[2] - box[0]) * scale;
    const boxHeight = (box[3] - box[1]) * scale;
    const colour = colourFor(object);

    context.strokeStyle = colour;
    context.lineWidth = stroke;
    context.strokeRect(x1, y1, boxWidth, boxHeight);

    const text = labelFor(object);
    const textWidth = context.measureText(text).width;
    const padding = Math.round(fontSize * 0.35);
    const labelHeight = fontSize + padding * 2;
    // Above the box normally, inside it when the box is against the top edge.
    const labelY = y1 - labelHeight >= 0 ? y1 - labelHeight : y1;

    context.fillStyle = colour;
    context.fillRect(x1 - stroke / 2, labelY, textWidth + padding * 2, labelHeight);
    context.fillStyle = "#0b1220";
    context.fillText(text, x1 + padding - stroke / 2, labelY + padding);

    // How close this object is to becoming a threat, drawn along the bottom
    // edge. Useful because a threat that is 90% of the way there looks identical
    // to one that just appeared, and an operator can act on the difference.
    const progress = Number(object.dwell_progress) || 0;
    if (!object.is_threat && progress > 0.02) {
      context.fillStyle = "rgba(15, 23, 42, 0.55)";
      context.fillRect(x1, y1 + boxHeight - stroke * 2, boxWidth, stroke * 2);
      context.fillStyle = colour;
      context.fillRect(x1, y1 + boxHeight - stroke * 2, boxWidth * Math.min(1, progress), stroke * 2);
    }
  });
}

function CameraCanvas({ baseUrl, cameraId, running, onFrame }) {
  const containerRef = useRef(null);
  const canvasRef = useRef(null);
  const onFrameRef = useRef(onFrame);
  const [visible, setVisible] = useState(true);
  const [live, setLive] = useState(false);

  // Held in a ref so a new callback identity on every parent render does not
  // tear down and restart the frame loop.
  useEffect(() => {
    onFrameRef.current = onFrame;
  }, [onFrame]);

  // A tile scrolled out of view stops asking for frames, and the worker stops
  // encoding them: its subscriber count drops to zero and JPEG encoding, the
  // largest cost in the pipeline after inference, becomes free for that camera.
  useEffect(() => {
    const node = containerRef.current;
    if (!node || typeof IntersectionObserver === "undefined") return undefined;
    const observer = new IntersectionObserver(
      (entries) => setVisible(entries.some((entry) => entry.isIntersecting)),
      { threshold: 0.05 }
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  const render = useCallback(
    (payload) =>
      new Promise((resolve) => {
        const image = new Image();
        image.onload = () => {
          const canvas = canvasRef.current;
          if (canvas) drawFrame(canvas, image, payload);
          resolve();
        };
        image.onerror = () => resolve();
        image.src = payload.image;
      }),
    []
  );

  useEffect(() => {
    if (!running || !visible) {
      setLive(false);
      return undefined;
    }

    const controller = new AbortController();
    let cancelled = false;
    let seq = -1;

    const wait = (ms) =>
      new Promise((resolve) => {
        setTimeout(resolve, ms);
      });

    // One long-poll in flight at a time. The request returns the moment a newer
    // frame exists, so this is event-driven despite being a loop: no fixed
    // interval to tune, and no polling faster than the camera produces.
    const loop = async () => {
      while (!cancelled) {
        try {
          const response = await fetch(
            `${baseUrl}/unattended-object/frame/${cameraId}?after=${seq}`,
            { signal: controller.signal, cache: "no-store" }
          );
          if (!response.ok) {
            if (cancelled) return;
            setLive(false);
            await wait(IDLE_RETRY_MS);
            continue;
          }
          const payload = await response.json();
          if (cancelled) return;
          if (onFrameRef.current) onFrameRef.current(payload);
          if (!payload.changed) continue;
          seq = payload.seq;
          await render(payload);
          if (!cancelled) setLive(true);
        } catch (error) {
          if (cancelled) return;
          setLive(false);
          await wait(IDLE_RETRY_MS);
        }
      }
    };

    loop();
    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [baseUrl, cameraId, running, visible, render]);

  return (
    <div className="camera-tile-video" ref={containerRef}>
      <canvas ref={canvasRef} className="video-feed video-feed-canvas" />
      {!live && (
        <div className="video-placeholder video-placeholder-overlay">
          {running ? "Connecting to camera…" : "Not started"}
        </div>
      )}
    </div>
  );
}

export default CameraCanvas;
