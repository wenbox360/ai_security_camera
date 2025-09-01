from picamera2 import Picamera2
from ultralytics import YOLO
import cv2

# Initialize camera
picam2 = Picamera2()
picam2.configure(picam2.create_preview_configuration(main={"format": "RGB888", "size": (640, 480)}))
picam2.start()

# Load YOLO model once
model = YOLO("yolo11n.pt")

# Capture frame
frame = picam2.capture_array()

# Run YOLO detection
results = model(frame)

# Save output image with boxes
results[0].save(filename="detection.jpg")

# Optional: show in window (only works with GUI)
# cv2.imshow("Detection", results[0].plot())
# cv2.waitKey(0)
# cv2.destroyAllWindows()s

