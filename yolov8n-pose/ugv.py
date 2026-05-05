import cv2
import numpy as np
from ultralytics import YOLO
import collections

# Load model
model = YOLO("yolov8n-pose.pt")

gesture_buffer = collections.deque(maxlen=5)

# ArUco setup
aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
parameters = cv2.aruco.DetectorParameters()

TARGET_MARKER_ID = 23

def get_gesture(keypoints):
    left_wrist = keypoints[9]
    right_wrist = keypoints[10]
    left_shoulder = keypoints[5]
    right_shoulder = keypoints[6]

    offset = 40

    left_up = left_wrist[1] < left_shoulder[1] - offset
    right_up = right_wrist[1] < right_shoulder[1] - offset

    dx = abs(left_wrist[0] - right_wrist[0])
    dy = abs(left_wrist[1] - right_wrist[1])

    if dx < 50 and dy < 50:
        return "BACKWARD"

    if left_up and right_up:
        return "FORWARD"
    elif right_up:
        return "RIGHT"
    elif left_up:
        return "LEFT"
    else:
        return "STOP"

cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    annotated = frame.copy()

    # -------------------------------
    # DETECT ARUCO MARKER
    # -------------------------------
    corners, ids, _ = cv2.aruco.detectMarkers(frame, aruco_dict, parameters=parameters)

    marker_center = None
    owner_visible = False

    if ids is not None:
        for i, marker_id in enumerate(ids):
            if marker_id[0] == TARGET_MARKER_ID:
                owner_visible = True

                pts = corners[i][0]
                cx = int(np.mean(pts[:, 0]))
                cy = int(np.mean(pts[:, 1]))
                marker_center = (cx, cy)

                cv2.polylines(annotated, [pts.astype(int)], True, (0,255,0), 2)
                cv2.putText(annotated, "OWNER", (cx, cy),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2)

    # -------------------------------
    # POSE DETECTION
    # -------------------------------
    results = model(frame, classes=[0])
    annotated = results[0].plot()

    gesture = "WAIT"

    if owner_visible and results[0].keypoints is not None:

        people = results[0].keypoints.data
        boxes = results[0].boxes.xyxy

        min_dist = float("inf")
        target_index = -1

        for i, box in enumerate(boxes):
            x1, y1, x2, y2 = box
            cx = (x1 + x2) / 2
            cy = (y1 + y2) / 2

            dist = np.linalg.norm(np.array([cx, cy]) - np.array(marker_center))

            if dist < min_dist:
                min_dist = dist
                target_index = i

        if target_index != -1:
            keypoints = people[target_index]
            gesture = get_gesture(keypoints)
            gesture_buffer.append(gesture)

            x1, y1, x2, y2 = boxes[target_index]
            cv2.rectangle(annotated,
                          (int(x1), int(y1)),
                          (int(x2), int(y2)),
                          (0,255,0), 3)

    # -------------------------------
    # SMOOTH OUTPUT
    # -------------------------------
    if len(gesture_buffer) > 0:
        final_gesture = max(set(gesture_buffer), key=gesture_buffer.count)
    else:
        final_gesture = gesture

    status = "OWNER DETECTED" if owner_visible else "WAITING FOR OWNER"

    cv2.putText(annotated, f"Gesture: {final_gesture}", (30,50),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2)

    cv2.putText(annotated, f"Status: {status}", (30,100),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,0,0), 2)

    cv2.imshow("UGV ARUCO SYSTEM", annotated)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()