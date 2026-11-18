----Smart-survelence -----------

python -m venv venv
py -3.12 -m venv venv
venv\Scripts\activate

pip install -r requirements.txt 

uvicorn backend.core.main:app --reload --host 0.0.0.0 --port 8000


 
==========for face recognization =================
python -m venv venv
venv\Scripts\activate 
pip install insightface[all]
pip install -r requirements.txt
uvicorn backend.core.main:app --reload --host 0.0.0.0 --port 8001


========= for un wanted ===============
py -3.12 -m venv venv
venv\Scripts\activate
python -m pip install -r requirements.txt
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8002

=============packaging =======================
python -m pip install pyinstaller
python -m PyInstaller --onefile core/main.py
pyinstaller --clean --noconfirm SmartSurveillance.spec
pyinstaller --clean --noconfirm Smart-Face-Recognization.spec
pyinstaller --clean --noconfirm smart-unattended-object.spec

pip install cachetools
==================== Needs to optimize====================
1.background process needs to start  form  scheduler tab from front end
2. all file name should be wel understanding
3. need to delete unwanted files ad folders
4. wel name of folders and files 
5. clear comments in frontend and backend 
6. styleshets needs to be optimize
7. database table name should be meening full
8. token expire needs to be fixed - fixed
9. more than 11 is not working 

===========================insert script of configuration ===========================

INSERT INTO configurations (key, value, description, created_by, updated_by, created_at, updated_at)
VALUES
('alertSoundPath', 'app/alert.wav', 'File path to the alert sound (wav/mp3/ogg).', 'migration', 'migration', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('alertOutputMode', 'system', 'Where the alert is played: system speakers or external hooter.', 'migration', 'migration', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('alertDurationSeconds', '15', 'Duration of alert sound in seconds.', 'migration', 'migration', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('whatsappPhone', '', 'Phone number to send WhatsApp alerts.', 'migration', 'migration', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('smsPhone', '', 'Phone number to send SMS alerts.', 'migration', 'migration', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('archiveDays', '30', 'Number of days to retain archived footage.', 'migration', 'migration', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('confidenceThreshold', '0.5', 'Minimum confidence score for detection (0–1).', 'migration', 'migration', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('frameSize', '640', 'Frame size used for video processing.', 'migration', 'migration', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('imageSize', '416', 'Image size used for detection model input.', 'migration', 'migration', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('focalLength', '24.0', 'Camera focal length in millimeters.', 'migration', 'migration', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('inferenceSize', '416', 'Inference image size for AI model.', 'migration', 'migration', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('snapshotCount', '5', 'Number of snapshots to capture when motion is detected.', 'migration', 'migration', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('detectionEnabled', 'True', 'Enable or disable live detection switch.', 'migration', 'migration', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('is_Camera_Detector', 'True', 'Enable or disable live Camera Detection switch.', 'migration', 'migration', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('live_Face_tracking_enabled', 'True', 'Enable or disable live Face Detection switch.', 'migration', 'migration', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);


