#! /usr/bin/env python

import cv2
import numpy as np
import rospy 
from geometry_msgs.msg import Twist

# --------- PARAMS --------------
# OUTPUT TOPIC 
vel_topic = '/turtle1/cmd_vel'

# MAX VALUE on each axes
max_speed = 5

# length of the joystick window in pixels
frame_size = 251

# set the centre of the joystick window
frame_centre = (125,125)

# set the colour of the joystick window (BGR)
frame_colour = (50,50,50)

# The control circle is the red outer circle 
# beyond which the mouse cursor will not hold the stick 
control_circle_radius = 120
control_circle_colour = (0,0,255)

# size of the joystck itself
stick_radius = 50

# --------------------------------
min_stick_colour = 60
latched = False
stick_centre = np.array((0,0))
Tcp = np.array([[ 1, 0, -frame_centre[0]], 
                [ 0,-1, frame_centre[1]], 
                [ 0, 0,               1]])

Tpc = np.array([[ 1, 0, frame_centre[0]], 
                [ 0,-1, frame_centre[1]], 
                [ 0, 0,               1]])

# ------------------------------------------

def run():
                
    def mag(vec):
        return np.sqrt(vec.dot(vec))

    def unitVec(vec):
        return vec/mag(vec)

    def pixels2cartesian(planarVec):
        return np.dot(Tcp, np.append(planarVec, 1))[0:2]

    def cartesian2pixels(planarVec):
        return np.dot(Tpc, np.append(planarVec, 1))[0:2].astype(int)

    def lightIntensity(stick_centre, stick_radius, min_stick_colour, control_circle_radius):
        return int(min_stick_colour + (255 - min_stick_colour)/(control_circle_radius -stick_radius)*mag(pixels2cartesian(stick_centre)))

    def updateStick(old_mouse_coords, new_mouse_coords, stick_centre, stick_radius, control_circle_radius):

        temp_stick_centre = stick_centre + (new_mouse_coords - old_mouse_coords)
        distance_from_centre = mag(temp_stick_centre)
        max_permissible = (control_circle_radius - stick_radius)
        if distance_from_centre > max_permissible:
            temp_stick_centre = max_permissible*unitVec(temp_stick_centre)
        return temp_stick_centre

    def draw_stick(img, stick_centre, stick_radius, min_stick_colour, control_circle_radius):
        cv2.circle(img, tuple(stick_centre), stick_radius, (0,0,0), -1)
        cv2.circle(img, tuple(stick_centre), stick_radius, (0, lightIntensity(stick_centre, stick_radius, min_stick_colour, control_circle_radius), 0), 3)

    def refresh(img, frame_centre, frame_colour, control_circle_radius, control_circle_colour):
        img[:,:] = tuple(frame_colour)
        cv2.circle(img, tuple(frame_centre), control_circle_radius, tuple(control_circle_colour), 2)

    def callback(event, x, y, flag, param):
        global old_mouse_coords, latched, stick_centre

        new_mouse_coords = pixels2cartesian(np.array((x,y)))

        if  event == cv2.EVENT_LBUTTONDOWN and mag(new_mouse_coords-stick_centre) < stick_radius:
            old_mouse_coords = new_mouse_coords
            latched = True

        elif event == cv2.EVENT_MOUSEMOVE and latched == True and mag(new_mouse_coords) < control_circle_radius:
            stick_centre = updateStick(old_mouse_coords, new_mouse_coords, stick_centre, stick_radius, control_circle_radius)
            refresh(frame, frame_centre, frame_colour, control_circle_radius, control_circle_colour)
            draw_stick(frame, cartesian2pixels(stick_centre), stick_radius, min_stick_colour, control_circle_radius)
            old_mouse_coords = new_mouse_coords

        elif (event == cv2.EVENT_LBUTTONUP) or (event == cv2.EVENT_MOUSEMOVE and latched == True and mag(new_mouse_coords) > control_circle_radius):
            latched = False
            stick_centre = np.array((0,0))
            refresh(frame, frame_centre, frame_colour, control_circle_radius, control_circle_colour)
            draw_stick(frame, cartesian2pixels(stick_centre), stick_radius, min_stick_colour, control_circle_radius)

    # --- INITIALIZING JOYSTICK GUI ---
    frame = np.full((frame_size, frame_size, 3), frame_colour, np.uint8)
    cv2.namedWindow('joystick', cv2.WINDOW_AUTOSIZE)
    cv2.setMouseCallback('joystick', callback)
    refresh(frame, frame_centre, frame_colour, control_circle_radius, control_circle_colour)
    draw_stick(frame, cartesian2pixels(stick_centre), stick_radius, min_stick_colour, control_circle_radius)

    # ----
    def kill_sequence():
        cv2.destroyAllWindows()
        print('shutting down')

    def scale_speed(val):
        return max_speed/float(control_circle_radius - stick_radius)*val
    
    rospy.init_node('turtlesim_joystick', anonymous=True)
    pub = rospy.Publisher(vel_topic, Twist, queue_size=10)
    velocity_input = Twist()
    rospy.on_shutdown(kill_sequence)

    velocity_input.linear.x = 0
    velocity_input.linear.y = 0
    velocity_input.linear.z = 0

    velocity_input.angular.x = 0
    velocity_input.angular.y = 0
    velocity_input.angular.z = 0

    while cv2.waitKey(1) != 27:
        cv2.imshow('joystick', frame)
        velocity_input.linear.x = scale_speed(stick_centre[0])
        velocity_input.linear.y = scale_speed(stick_centre[1])
        
        
        pub.publish(velocity_input)
        # rospy.loginfo(velocity_input)


if __name__ == '__main__':
    try:
        print('press esc to close when joystick window is selected')
        run()
    except rospy.ROSInterruptException:
        pass
