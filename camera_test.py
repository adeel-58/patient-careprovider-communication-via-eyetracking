import cv2

def list_cameras():
    i = 0
    while True:
        cap = cv2.VideoCapture(i)
        if not cap.isOpened():
            print(f"No camera found at index {i}")
            cap.release() # Release if not opened to avoid resource issues
            if i > 5: # Limit the search to a reasonable number of indices
                break
            i += 1
            continue
        
        print(f"Camera found at index {i}")
        
        # Optionally, display a frame to confirm it's the right camera
        ret, frame = cap.read()
        if ret:
            cv2.imshow(f"Camera {i}", frame)
            cv2.waitKey(1000) # Show for 1 second
            cv2.destroyWindow(f"Camera {i}")
        
        cap.release()
        i += 1
    cv2.destroyAllWindows()

if __name__ == "__main__":
    list_cameras()