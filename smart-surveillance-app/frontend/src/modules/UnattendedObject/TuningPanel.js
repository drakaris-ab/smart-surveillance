import React, { useCallback, useEffect, useState } from "react";
import axios from "axios";

const client = axios.create({ timeout: 8000 });

function Control({ param, value, onChange }) {
  const id = `tune-${param.name}`;

  if (param.kind === "bool") {
    return (
      <label className="tune-toggle" htmlFor={id}>
        <input
          id={id}
          type="checkbox"
          checked={Boolean(value)}
          disabled={param.restart_required}
          onChange={(event) => onChange(param.name, event.target.checked)}
        />
        <span>{value ? "on" : "off"}</span>
      </label>
    );
  }

  if (param.kind === "str") {
    return (
      <input
        id={id}
        type="text"
        className="tune-text"
        value={value ?? ""}
        disabled={param.restart_required}
        onChange={(event) => onChange(param.name, event.target.value)}
      />
    );
  }

  // Slider and number box over the same value: the slider is for sweeping a
  // range, the box for entering a figure someone gave you. Both are bounded by
  // the schema, so neither can reach a value the backend would clamp.
  return (
    <div className="tune-range">
      <input
        id={id}
        type="range"
        min={param.min}
        max={param.max}
        step={param.step}
        value={Number(value)}
        disabled={param.restart_required}
        onChange={(event) => onChange(param.name, Number(event.target.value))}
      />
      <input
        type="number"
        className="tune-number"
        min={param.min}
        max={param.max}
        step={param.step}
        value={Number(value)}
        disabled={param.restart_required}
        onChange={(event) => onChange(param.name, Number(event.target.value))}
      />
    </div>
  );
}

function TuningPanel({ baseUrl, notify }) {
  const [open, setOpen] = useState(false);
  const [schema, setSchema] = useState(null);
  const [draft, setDraft] = useState({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [rejected, setRejected] = useState({});

  const load = useCallback(async () => {
    try {
      const { data } = await client.get(`${baseUrl}/unattended-object/tuning`);
      setSchema(data);
      setDraft({});
      setRejected({});
      setError("");
    } catch (err) {
      setError("Could not reach the detection worker.");
    }
  }, [baseUrl]);

  // Fetched on first open rather than on mount: the panel is a tool, and a page
  // that is only being watched should not pay for it.
  useEffect(() => {
    if (open && !schema) load();
  }, [open, schema, load]);

  const valueOf = useCallback(
    (param) => (param.name in draft ? draft[param.name] : param.value),
    [draft]
  );

  const stage = useCallback((name, value) => {
    setDraft((previous) => ({ ...previous, [name]: value }));
  }, []);

  const pending = Object.keys(draft).length;

  const save = async () => {
    if (!pending) return;
    setBusy(true);
    try {
      const { data } = await client.patch(`${baseUrl}/unattended-object/tuning`, {
        values: draft,
      });
      setRejected(data.rejected || {});
      const applied = Object.keys(data.applied || {}).length;
      if (notify) {
        notify(
          Object.keys(data.rejected || {}).length ? "warning" : "success",
          applied
            ? `Applied ${applied} parameter${applied === 1 ? "" : "s"} (revision ${data.revision}).`
            : "Nothing changed."
        );
      }
      await load();
    } catch (err) {
      const detail = err.response?.data?.detail;
      setRejected(detail?.rejected || {});
      setError(typeof detail === "string" ? detail : "The worker rejected the change.");
    } finally {
      setBusy(false);
    }
  };

  const resetAll = async () => {
    setBusy(true);
    try {
      await client.post(`${baseUrl}/unattended-object/tuning/reset`);
      if (notify) notify("success", "Detection parameters back to their startup values.");
      await load();
    } catch (err) {
      setError("Could not reset.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="tune-panel">
      <button
        type="button"
        className="tune-header"
        onClick={() => setOpen((was) => !was)}
        aria-expanded={open}
      >
        <span>Detection tuning</span>
        <span className="tune-header-meta">
          {schema ? `revision ${schema.revision}` : ""}
          {pending ? ` · ${pending} unsaved` : ""}
          <i className={`tune-chevron ${open ? "up" : ""}`} aria-hidden="true" />
        </span>
      </button>

      {open && (
        <div className="tune-body">
          <p className="tune-intro">
            Changes take effect within a frame or two on every running camera. Track
            ids, owner bindings and dwell timers are kept, so nothing you are
            watching is reset. Nothing is saved to disk — restart and these return
            to the values in the environment. The <code>UOD_…</code> name beside
            each control is how you make one permanent.
          </p>

          {error && <p className="tune-error">{error}</p>}

          {(schema?.warnings || []).map((warning) => (
            <p className="tune-warning" key={warning}>
              {warning}
            </p>
          ))}

          {!schema && <p>Loading…</p>}

          {(schema?.groups || []).map((group) => (
            <div className="tune-group" key={group.group}>
              <h4>{group.group}</h4>
              {group.params.map((param) => (
                <div
                  className={`tune-row${param.name in draft ? " dirty" : ""}`}
                  key={param.name}
                >
                  <div className="tune-label">
                    <label htmlFor={`tune-${param.name}`}>{param.label}</label>
                    <code>{param.env}</code>
                    {param.modified && <span className="tune-tag">changed</span>}
                    {param.restart_required && (
                      <span className="tune-tag restart">restart required</span>
                    )}
                  </div>
                  <Control param={param} value={valueOf(param)} onChange={stage} />
                  <p className="tune-help">
                    {param.help} <span>Default {String(param.default)}.</span>
                  </p>
                  {rejected[param.name] && (
                    <p className="tune-error">{rejected[param.name]}</p>
                  )}
                </div>
              ))}
            </div>
          ))}

          {schema && (
            <div className="tune-actions">
              <button type="button" onClick={save} disabled={busy || !pending}>
                {busy ? "Applying…" : `Apply${pending ? ` (${pending})` : ""}`}
              </button>
              <button type="button" onClick={() => setDraft({})} disabled={!pending}>
                Discard
              </button>
              <button type="button" onClick={resetAll} disabled={busy}>
                Reset all to startup
              </button>
            </div>
          )}
        </div>
      )}
    </section>
  );
}

export default TuningPanel;
