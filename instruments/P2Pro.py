#!/usr/bin/env python3
# P2Pro display application with locked scale
# Based on ideas from https://github.com/leswright1977/PyThermalCamera

import cv2
import numpy as np
import PIL.Image
import PIL.ImageDraw
import PIL.ImageFont
from matplotlib import font_manager
import functools
import time

class P2Pro:
    '''Capture images from Infiray P2Pro thermal camera'''
    
    # Temperature in Celsius and RGB color
    default_palette = [
        (-20,    0,   0,   0), # Black
        (  0,    0,   0, 255), # Blue
        ( 20,    0, 128, 128), # Cyan
        ( 40,    0, 255,   0), # Green
        ( 60,  255, 255,   0), # Yellow
        ( 80,  200, 128,   0), # Orange
        ( 100, 255,   0,   0), # Red
        ( 120, 200,   0, 255)  # Purple
    ]
    
    def __init__(self, device = "/dev/instruments/P2Pro"):
        self.device = device
        self.palette = np.array(P2Pro.default_palette)
        
        self.fontprops = font_manager.FontProperties(family='sans serif')
    
    @functools.cached_property
    def video(self):
        '''Open video stream on first access'''
        video = cv2.VideoCapture(self.device, cv2.CAP_V4L)
        video.set(cv2.CAP_PROP_CONVERT_RGB, 0.0)
        return video
    
    def capture(self):
        '''Capture frame and return as numpy array of temperatures'''

        for i in range(100):
            ret, frame = self.video.read()
            if ret: break
            time.sleep(0.01)
        else:
            raise Exception("Failed to capture video frame")
        
        # The lower half of the image contains 16-bit temperature readings
        # Convert to Celsius scale
        image, thermal = np.array_split(frame, 2)
        temperatures = thermal[:,:,0].astype('float') + thermal[:,:,1].astype('float') * 256
        temperatures = (temperatures / 64) - 273.15
        return temperatures
    
    def map_colors(self, temperatures):
        '''Perform color mapping for temperature values based on palette.
        Note: Uses absolute color scale instead of automatic scaling.
        '''
        r = np.interp(temperatures, self.palette[:,0], self.palette[:,1])
        g = np.interp(temperatures, self.palette[:,0], self.palette[:,2])
        b = np.interp(temperatures, self.palette[:,0], self.palette[:,3])
        rgb = np.stack((r,g,b), axis = 2).astype(np.uint8)
        return PIL.Image.fromarray(rgb, 'RGB')
    
    def draw_scale(self, img, x, y, w, h):
        '''Draw palette scale to image'''
        
        # Draw color scale
        mintemp = np.min(self.palette[:,0])
        maxtemp = np.max(self.palette[:,0])
        temps = np.tile(np.linspace(maxtemp, mintemp, h), (w, 1)).transpose()
        colors = self.map_colors(temps)
        img.paste(colors, (x, y))
        
        # Draw texts
        draw = PIL.ImageDraw.Draw(img)
        fontpath = font_manager.findfont(self.fontprops)
        font = PIL.ImageFont.truetype(fontpath, 10)
        for t, r, g, b in self.palette:
            ypos = h - (t - mintemp) / (maxtemp - mintemp) * h + y
            draw.line(((x + w, ypos), (x + w + 5, ypos)), (r,g,b), 1)
            draw.text((x + w + 7, ypos), "%0.0f °C" % t, (255, 255, 255),
                      font, anchor = 'lm')
    
    def draw_point(self, img, x, y, text):
        '''Hilight point in image and add explanation text'''
        draw = PIL.ImageDraw.Draw(img)
        fontpath = font_manager.findfont(self.fontprops)
        font = PIL.ImageFont.truetype(fontpath, 10)

        draw.ellipse((x-3,y-3,x+3,y+3), outline = (255,255,255))
        draw.line(((x+3, y), (x + 5, y)), (255,255,255), 1)
        draw.text((x + 8, y), text, (255,255,255), font, anchor = 'lm')
    
    def snapshot(self, scale = True, minpoint = True, maxpoint = True, midpoint = True):
        '''Capture frame as false-color image.
        Optionally mark minimum, maximum and center temperatures and scale.
        '''
        temps = self.capture()
        h, w = temps.shape
        thermimg = self.map_colors(temps)
        thermimg = thermimg.resize((w * 2, h * 2))

        if scale:
            scalew = 80
        else:
            scalew = 0
        
        img = PIL.Image.new("RGB", (w * 2 + scalew, h * 2))
        img.paste(thermimg)
        
        if scale:
            self.draw_scale(img, w * 2 + 5, 10, 10, h * 2 - 20)
        
        if minpoint:
            my, mx = np.unravel_index(np.argmin(temps), temps.shape)
            self.draw_point(img, mx * 2, my * 2, "min %0.1f °C" % np.min(temps))
        
        if maxpoint:
            my, mx = np.unravel_index(np.argmax(temps), temps.shape)
            self.draw_point(img, mx * 2, my * 2, "max %0.1f °C" % np.max(temps))
        
        if midpoint:
            mx = w // 2
            my = h // 2
            self.draw_point(img, mx * 2, my * 2, "%0.1f °C" % temps[my,mx])
        
        return img

if __name__ == '__main__':
    cam = P2Pro()
    
    while True:
        img = cam.snapshot()
        cv2.imshow('P2Pro', np.array(img)[:,:,::-1])
        
        if cv2.waitKey(50) in [ord('q'), ord('Q'), 27]:
            break
        
        if cv2.getWindowProperty('P2Pro',cv2.WND_PROP_AUTOSIZE) == -1:
            break

