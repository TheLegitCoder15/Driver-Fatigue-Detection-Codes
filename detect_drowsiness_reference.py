# USAGE
# python detect_drowsiness.py --shape-predictor shape_predictor_68_face_landmarks.dat
# python detect_drowsiness.py --shape-predictor shape_predictor_68_face_landmarks.dat --alarm alarm.wav

# import the necessary packages
from scipy.spatial import distance as dist
from imutils.video import VideoStream
from imutils import face_utils
from threading import Thread
from openpyxl import Workbook
import numpy as np
import pandas as pd
import playsound
import argparse
import imutils
import time
import dlib
import cv2

def sound_alarm(path):
    # play an alarm sound
    playsound.playsound(path)

def eye_aspect_ratio(eye):
    # compute the euclidean distances between the two sets of
    # vertical eye landmarks (x, y)-coordinates
    A = dist.euclidean(eye[1], eye[5])
    B = dist.euclidean(eye[2], eye[4])

    # compute the euclidean distance between the horizontal
    # eye landmark (x, y)-coordinates
    C = dist.euclidean(eye[0], eye[3])

    # compute the eye aspect ratio
    ear = (A + B) / (2.0 * C)

    # return the eye aspect ratio
    return ear

def blink_rate_evaluation(blink_rate):
    if blink_rate >= EYE_BLINK_RATE_LOW and blink_rate <= EYE_BLINK_RATE_HIGH:
        blink_level = "Normal"

    elif blink_rate < EYE_BLINK_RATE_LOW:
        blink_level = "Low"

    elif blink_rate > EYE_BLINK_RATE_HIGH:
        blink_level = "High"

    else:
        blink_level = "N/A"

    return blink_level


# construct the argument parse and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("-p", "--shape-predictor", required=True,
                help="path to facial landmark predictor")
ap.add_argument("-a", "--alarm", type=str, default="",
                help="path alarm .WAV file")
ap.add_argument("-w", "--webcam", type=int, default=0,
                help="index of webcam on system")
args = vars(ap.parse_args(['-p=shape_predictor_68_face_landmarks.dat','-a=alarm.wav']))

# Guide for THRESHOLD determination:
# Alert: Normal Blink Rate(0.25-0.33blink/s) and Normal Blink Duration(100-400ms)
#     or Low blink rate(<0.25blink/s) and Normal Blink Duration(100-400ms)
# Low Alertness: Normal blink rate(0.25-0.33blink/s) and Long Blink Duration(400ms-1s)
#             or Low blink rate(<0.25blink/s) and Long Blink Duration(400ms-1s)
# Drowsy: High blink rate(>0.33blink/s) and Long Blink Duration(400ms-1s)
#      or Normal Blink rate(0.25-0.33blink/s) and Long Blink Duration(400ms-1s)
# Sleeping: Low Blink rate(<0.25blink/s) and Very Long Blink Duration(>1s)
EYE_AR_THRESH = 0.20
EYE_AR_1000MS_FRAMES = 48
EYE_AR_400MS_FRAMES = 12
EYE_AR_100MS_FRAMES = 3
EYE_BLINK_RATE_LOW = 0.25
EYE_BLINK_RATE_HIGH = 0.33

# initialization of variables
COUNTER = 0
TOTAL = 0
blink_rate = 0
processing_time = 0
blink_duration_level = "Normal"
ALARM_ON = False
blink = False

# initialize dlib's face detector (HOG-based) and then create
# the facial landmark predictor
print("[INFO] loading facial landmark predictor...")
detector = dlib.get_frontal_face_detector()
predictor = dlib.shape_predictor(args["shape_predictor"])

# grab the indexes of the facial landmarks for the left and
# right eye, respectively
(lStart, lEnd) = face_utils.FACIAL_LANDMARKS_IDXS["left_eye"]
(rStart, rEnd) = face_utils.FACIAL_LANDMARKS_IDXS["right_eye"]

# initialize data frame
df = pd.DataFrame()

# start the video stream thread
print("[INFO] starting video stream thread...")
vs = VideoStream(src=args["webcam"]).start()
time.sleep(1.0)

# loop over frames from the video stream
while True:
    # add start variable for computation of processing time
    # grab the frame from the threaded video file stream, resize
    # it, and convert it to grayscale
    # channels)
    start = time.time()
    frame = vs.read()
    frame = imutils.resize(frame, width=450)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # detect faces in the grayscale frame
    rects = detector(gray, 0)

    # loop over the face detections
    for rect in rects:

        # get coordinates generated by detector, then
        # draw rectangle around the face to indicate
        # face detection
        x1 = rect.left()
        y1 = rect.top()
        x2 = rect.right()
        y2 = rect.bottom()
        cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 255, 0), 1)

        # determine the facial landmarks for the face region, then
        # convert the facial landmark (x, y)-coordinates to a NumPy
        # array
        shape = predictor(gray, rect)
        shape = face_utils.shape_to_np(shape)

        # extract the left and right eye coordinates, then use the
        # coordinates to compute the eye aspect ratio for both eyes
        leftEye = shape[lStart:lEnd]
        rightEye = shape[rStart:rEnd]
        leftEAR = eye_aspect_ratio(leftEye)
        rightEAR = eye_aspect_ratio(rightEye)

        # average the eye aspect ratio together for both eyes
        ear = (leftEAR + rightEAR) / 2.0    

        # compute the convex hull for the left and right eye, then
        # visualize each of the eyes
        leftEyeHull = cv2.convexHull(leftEye)
        rightEyeHull = cv2.convexHull(rightEye)
        cv2.drawContours(frame, [leftEyeHull], -1, (0, 255, 0), 1)
        cv2.drawContours(frame, [rightEyeHull], -1, (0, 255, 0), 1)

        # check to see if the eye aspect ratio is below the blink
        # threshold, and if so, increment the blink frame counter
        if ear < EYE_AR_THRESH:
            COUNTER += 1

            # if the eyes were closed for a sufficient number of
            # then sound the alarm
            if COUNTER >= EYE_AR_1000MS_FRAMES:
                # if the alarm is not on, turn it on
                if not ALARM_ON:
                    ALARM_ON = True

                    # check to see if an alarm file was supplied,
                    # and if so, start a thread to have the alarm
                    # sound played in the background
                    if args["alarm"] != "":
                        t = Thread(target=sound_alarm,
                                   args=(args["alarm"],))
                        t.deamon = True
                        t.start()

                    blink_duration_level = "Very Long"

                # draw an alarm on the frame
                cv2.putText(frame, "DROWSINESS ALERT!", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

            # if the counter is less than EYE_AR_1000MS_FRAMES threshold
            # change boolean value of blink
            elif COUNTER >= EYE_AR_400MS_FRAMES and COUNTER <= EYE_AR_1000MS_FRAMES:
                blink_duration_level = "Long"
                blink = True

            elif COUNTER >= EYE_AR_100MS_FRAMES and COUNTER <= EYE_AR_400MS_FRAMES:
                blink_duration_level = "Normal"
                blink = True

            else:
                blink = True

        # otherwise, the eye aspect ratio is not below the blink
        # threshold, so reset the counter and alarm
        else:
            # if a blink has occured increment
            # blink counter (TOTAL) and invert blink boolean logic
            if blink == True:
                TOTAL += 1
                blink = False

            COUNTER = 0
            ALARM_ON = False

        # get the end time of processing one frame
        # subtract the end time to start time to get the processing time
        # of a single frame and invert to get fps.
        # additionaly, compute for the overall processing by
        # incrementing the variable (processing_time) by the difference of start
        # and end variable.
        # after processing time, compute for the blink rate
        end = time.time()
        fps = 1/(end-start)
        processing_time += (end-start)
        blink_rate = TOTAL / processing_time

        blink_level = blink_rate_evaluation(blink_rate)
        
        # Update the dataframe after processing a single frame
        df = df.append({'Blink': TOTAL, 'blink_rate': blink_rate,
            'EAR': ear, 'FPS': fps}, ignore_index=True)

        # draw the computed eye aspect ratio on the frame to help
        # with debugging and setting the correct eye aspect ratio
        # thresholds and frame counters
        cv2.putText(frame, "Blink Rate Level: {:}".format(blink_level), 
                    (120, 300),cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        cv2.putText(frame, "Blink Duration Level: {:}".format(blink_duration_level), 
                    (120, 330),cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        cv2.putText(frame, "Blink: {:}".format(TOTAL), (10, 330),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        cv2.putText(frame, "EAR: {:.2f}".format(ear), (330, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

    # show the frame
    cv2.imshow("Frame", frame)
    key = cv2.waitKey(1) & 0xFF

    # if the `q` key was pressed, break from the loop
    if key == ord("q"):
        # Code below is for extract dataframe to excel
        # when q button is pressed
        #export_excel = df.to_excel(r'C:\Users\user\Documents\Github\Driver-Fatigue-Detection-Codes\Data\export_dataframe.xlsx',
        #                          index=None, header=True)
        break

# do a bit of cleanup
cv2.destroyAllWindows()
vs.stop()