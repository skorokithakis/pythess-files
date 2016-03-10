#!/usr/bin/python
# -*- coding: utf-8 -*-

import kivy
from kivy.app import App
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.scatter import Scatter
from kivy.uix.screenmanager import Screen, ScreenManager, FadeTransition
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.carousel import Carousel
from os import listdir
from os.path import isfile, join

#kivy.require('1.9.1')

images_path = "images/"
carousel_images = [f for f in listdir(images_path) if isfile(join(images_path, f))]

#print carousel_images


class ImagesCarousel(Carousel):
    """
        #STEP 4
        A simple carousel to load our images
        to avoid scatter and make it simple
        remove scatter and replace add_widget(image_to_add)
    """
    def __init__(self,*args, **kwargs):
        super(ImagesCarousel, self).__init__(**kwargs)
        for image in carousel_images:
            scatter = Scatter(pos=(100,200), scale=4, do_scale=True)
            image_to_add = Image(source=images_path+image)
            scatter.add_widget(image_to_add)
            self.add_widget(scatter)


class ScreenOne(Screen):
    """
        STEP 2
        This is screen 1 -> see class PyThess(App) 2nd line in build
    """
    def __init__(self,**kwargs):
        super(ScreenOne, self).__init__(**kwargs)
        my_box = FloatLayout(orientation='vertical')
        button1 = Button(text="To the next screen",color=[1,1,1,1],size_hint_y=0.1, size_hint_x=1, pos_hint={'x':0, 'y': 0.9})
        button1.bind(on_press=self.screen_changer1)
        label = Label(text='Hello PyThess', font_size='40sp', pos_hint={'x':0, 'y': 0.3})
        my_box.add_widget(button1)
        my_box.add_widget(label)
        self.add_widget(my_box)

    def screen_changer1(self, *args):
        self.manager.current = 'screen2'


class ScreenTwo(Screen):
    """
        #STEP 3
        This is screen 2 -> see class PyThess(App) 3rd line in build
    """
    def __init__ (self,**kwargs):
        super (ScreenTwo, self).__init__(**kwargs)
        my_box = FloatLayout(orientation='vertical')
        my_box1 = FloatLayout(orientation='vertical',size_hint_y=0.9,size_hint_x = 1,  pos_hint={'x':0, 'y': 0})
        button1 = Button(text="To the previous screen",color=[0,0,0,1],size_hint_y=0.1, size_hint_x=1, pos_hint={'x':0, 'y': 0.9})
        button1.bind(on_press=self.screen_changer1)
        my_box.add_widget(button1)
        local_carousel = ImagesCarousel(direction='right') # Here we create the new Carousel
        my_box1.add_widget(local_carousel)
        my_box.add_widget(my_box1)
        self.add_widget(my_box)

    def screen_changer1(self, *args):
        self.manager.current = 'screen1'


class PyThess(App):
    """
        #STEP 1
        The basic app class. Here we load the screen manager
    """
    def build(self):
        self.my_screenmanager = ScreenManager(transition=FadeTransition())
        screen1 = ScreenOne(name='screen1')
        screen2 = ScreenTwo(name='screen2')
        self.my_screenmanager.add_widget(screen1)
        self.my_screenmanager.add_widget(screen2)
        return self.my_screenmanager


if __name__ == '__main__':
    PyThess().run()
