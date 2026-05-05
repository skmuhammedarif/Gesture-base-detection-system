from ultralytics import YOLO
import cv2
import collections

model = YOLO("yolov8n-pose.pt")

gesture_buffer = collections.deque(maxlen=5)

def get_gesture(keypoints):
    left_wrist = keypoints[9]
    right_wrist = keypoints[10]
    left_shoulder = keypoints[5]
    right_shoulder = keypoints[6]

    offset = 40  # for up detection

    # -------------------------------
    # HAND POSITION
    # -------------------------------
    left_up = left_wrist[1] < left_shoulder[1] - offset
    right_up = right_wrist[1] < right_shoulder[1] - offset

    # -------------------------------
    # NAMASTE DETECTION (KEY PART 🔥)
    # -------------------------------
    dx = abs(left_wrist[0] - right_wrist[0])
    dy = abs(left_wrist[1] - right_wrist[1])

    # threshold (adjust if needed)
    if dx < 50 and dy < 50:
        return "BACKWARD 👇"

    # -------------------------------
    # NORMAL LOGIC
    # -------------------------------
    if left_up and right_up:
        return "FORWARD 👍"

    elif right_up:
        return "RIGHT 👉"

    elif left_up:
        return "LEFT 👈"

    else:
        return "STOP ✋"

cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    results = model(frame)

    annotated = results[0].plot()

    gesture = "NO PERSON"

    if results[0].keypoints is not None:

        people = results[0].keypoints.data
        boxes = results[0].boxes.xyxy  # bounding boxes

        # -------------------------------
        # SELECT LARGEST PERSON
        # -------------------------------
        max_area = 0
        target_index = -1

        for i, box in enumerate(boxes):
            x1, y1, x2, y2 = box
            area = (x2 - x1) * (y2 - y1)

            if area > max_area:
                max_area = area
                target_index = i

        # -------------------------------
        # USE ONLY TARGET PERSON
        # -------------------------------
        if target_index != -1:
            keypoints = people[target_index]

            gesture = get_gesture(keypoints)

            gesture_buffer.append(gesture)

            # Highlight selected person
            x1, y1, x2, y2 = boxes[target_index]
            cv2.rectangle(annotated,
                          (int(x1), int(y1)),
                          (int(x2), int(y2)),
                          (0, 255, 0), 3)

    # Smooth gesture
    if len(gesture_buffer) > 0:
        final_gesture = max(set(gesture_buffer), key=gesture_buffer.count)
    else:
        final_gesture = "NO PERSON"

    cv2.putText(annotated, f"Gesture: {final_gesture}", (30, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2)

    cv2.imshow("UGV Multi-Person Control", annotated)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()