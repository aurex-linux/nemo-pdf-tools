#!/usr/bin/python3
# -*- coding: iso-8859-1 -*-
#
__author__="atareao"
__date__ ="$22-jan-2012$"
#
#
# Copyright (C) 2012 Lorenzo Carbonell
# lorenzo.carbonell.cerezo@gmail.com
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#
#
from gi.repository import Nemo as FileManager
from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import Poppler
import tempfile
import cairo
import math
import shutil
import os
import sys

import locale
import gettext

LANGDIR = '/usr/share/locale-langpack'
APP = 'nemo-pdf-tools'
ICON = 'application-pdf'
VERSION = '0.7.1-0extras13.10.3'

locale.setlocale(locale.LC_ALL, '')
gettext.bindtextdomain(APP, LANGDIR)
gettext.textdomain(APP)
_ = gettext.gettext	

EXTENSIONS_TO = ['.djvu','.html','.txt','.jpg','.png']
EXTENSIONS_FROM = ['.bmp','.dds','.exif','.gif','.jpg','.jpeg','.jp2','.jpx','.pcx','.png','.pnm','.ras','.tga','.tif','.tiff','.xbm','.xpm']

SEPARATOR = u'\u2015' * 10
RESOLUTION = 110.0/72.0
MMTOPIXEL = 3.779527559055
MMTOPDF = 4
TOP = -1
MIDLE = 0
BOTTOM = 1
LEFT = -1
CENTER = 0
RIGHT = 1 
ROTATE_000 = 0.0
ROTATE_090 = 90.0
ROTATE_180 = 180.0
ROTATE_270 = 270.0

########################################################################
class MiniView(Gtk.DrawingArea):
	def __init__(self,width=400.0,height=420.00,margin=10.0,border=2.0,force=False):
		Gtk.DrawingArea.__init__(self)
		self.add_events(Gdk.EventMask.POINTER_MOTION_MASK | Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.BUTTON_RELEASE_MASK)
		self.height = height
		self.width = width
		self.image_surface = None
		self.margin = margin
		self.border = border
		self.page = None
		self.zoom = 1
		self.rotation_angle = 0.0
		self.flip_horizontal = False
		self.flip_vertical = False
		self.page_width = -1
		self.page_height = -1
		self.margin_width = -1
		self.margin_height = -1
		self.image = None
		self.text = None
		self.color = [0,0,0,1]
		self.font = 'Ubuntu'
		self.size = 12
		self.position_vertical = TOP
		self.position_horizontal = LEFT		
		self.connect('draw', self.on_expose, None)
		self.set_size_request(self.width, self.height)
		
	def on_expose(self, widget, cr, data):		
		if self.page:
			if self.rotation_angle == 0.0 or self.rotation_angle == 2.0:
				zw = (self.width-2.0*self.margin)/self.or_width
				zh = (self.height-2.0*self.margin)/self.or_height
				if zw < zh:
					self.zoom = zw
				else:
					self.zoom = zh
				self.page_width = self.or_width*self.zoom
				self.page_height = self.or_height*self.zoom
				self.margin_width = (self.width - self.page_width)/2.0
				self.margin_height = (self.height - self.page_height)/2.0
			else:
				zw = (self.width-2.0*self.margin)/self.or_height
				zh = (self.height-2.0*self.margin)/self.or_width
				if zw < zh:
					self.zoom = zw
				else:
					self.zoom = zh
				self.page_width = self.or_height*self.zoom
				self.page_height = self.or_width*self.zoom
				self.margin_width = (self.width - self.page_width)/2.0
				self.margin_height = (self.height - self.page_height)/2.0				
			self.image_surface = cairo.ImageSurface(cairo.FORMAT_RGB24,int(self.page_width),int(self.page_height)) 
			context = cairo.Context(self.image_surface)
			context.save()
			context.set_source_rgba(1.0, 1.0, 1.0, 1.0)
			context.paint()
			mtr = cairo.Matrix()
			mtr.rotate(self.rotation_angle*math.pi/2.0)
			mtr.scale(self.zoom*RESOLUTION,self.zoom*RESOLUTION)
			context.transform(mtr)
			if self.rotation_angle == 1.0:
					context.translate(0.0,-self.page_width/self.zoom/RESOLUTION)
			elif self.rotation_angle == 2.0:
					context.translate(-self.page_width/self.zoom/RESOLUTION,-self.page_height/self.zoom/RESOLUTION)
			elif self.rotation_angle == 3.0:
					context.translate(-self.page_height/self.zoom/RESOLUTION,0.0)
			self.page.render(context)		
			context.restore()
			if self.image:
				watermark_surface = cairo.ImageSurface.create_from_png(self.image)
				img_height = watermark_surface.get_height()
				img_width = watermark_surface.get_width()
				# scale image and add it
				context.save()				
				print(self.or_width,self.or_height)
				if self.position_vertical == TOP:
					y = 0
				elif self.position_vertical == MIDLE:
					y = (self.or_height - img_height/MMTOPIXEL)/2					
				elif self.position_vertical == BOTTOM:
					y = self.or_height - img_height/MMTOPIXEL
				if self.position_horizontal == LEFT:
					x = 0
				elif self.position_horizontal == CENTER:
					x = (self.or_width - img_width/MMTOPIXEL)/2
				elif self.position_horizontal == RIGHT:
					x = self.or_width - img_width/MMTOPIXEL	
				context.translate(x*self.zoom,y*self.zoom)
				context.scale(self.zoom/MMTOPIXEL,self.zoom/MMTOPIXEL)
				context.set_source_surface(watermark_surface)
				context.paint()
			if self.text:
				context.save()
				context.set_source_rgba(*self.color)
				context.select_font_face(self.font)
				context.set_font_size(self.size)
				xbearing, ybearing, font_width, font_height, xadvance, yadvance = context.text_extents(self.text)
				if self.position_vertical == TOP:
					y = font_height
				elif self.position_vertical == MIDLE:
					y = (self.or_height + font_height)/2					
				elif self.position_vertical == BOTTOM:
					y = self.or_height
				if self.position_horizontal == LEFT:
					x = 0
				elif self.position_horizontal == CENTER:
					x = (self.or_width - font_width)/2
				elif self.position_horizontal == RIGHT:
					x = self.or_width - font_width	+ xbearing
				context.move_to(x*self.zoom,y*self.zoom)
				context.translate(x*self.zoom,y*self.zoom)
				context.scale(self.zoom,self.zoom)
				context.show_text(self.text)
				context.restore()				
		cr.save()		
		cr.set_source_rgba(0.0, 0.0, 0.0, 0.5)
		cr.rectangle(self.margin_width-self.border, self.margin_height-self.border,
		self.page_width+2.0*self.border, self.page_height+2.0*self.border)
		cr.stroke()
		cr.restore()
		#
		if self.flip_vertical:
			cr.scale(1,-1)
			cr.translate(0,-(2*self.margin_height+self.page_height))
		if self.flip_horizontal:
			cr.scale(-1,1)
			cr.translate(-(2*self.margin_width+self.page_width),0)
		if self.page:
			cr.set_source_surface(self.image_surface,self.margin_width,self.margin_height)
			cr.paint()

	def set_page(self, page):
		self.page = page
		self.rotation_angle = 0.0
		self.drawings = []		
		self.or_width, self.or_height = self.page.get_size()
		self.or_width = int(self.or_width*RESOLUTION)
		self.or_height = int(self.or_height*RESOLUTION)
		self.queue_draw()
		
	def set_rotation_angle(self,rotation_angle):
		self.rotation_angle = rotation_angle
		self.queue_draw()
		
	def set_flip_horizontal(self,flip_horizontal):
		self.flip_horizontal = flip_horizontal
		self.queue_draw()
		
	def set_flip_vertical(self,flip_vertical):
		self.flip_vertical = flip_vertical
		self.queue_draw()
		
	def set_image_position_vertical(self,position_vertical):
		self.position_vertical = position_vertical
		self.queue_draw()
		
	def set_image_position_horizontal(self,position_horizontal):
		self.position_horizontal = position_horizontal
		self.queue_draw()
	
	def set_text(self,text):
		self.text = text
		self.queue_draw()

	def set_image(self,image):
		self.image = image
		self.queue_draw()

	def refresh(self):
		self.queue_draw()

class PaginateDialog(Gtk.Dialog):
	def __init__(self,filename=None):
		Gtk.Dialog.__init__(self,_('Paginate'),None,Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,(Gtk.STOCK_OK, Gtk.ResponseType.ACCEPT,Gtk.STOCK_CANCEL,Gtk.ResponseType.CANCEL))
		self.set_size_request(500, 140)
		self.set_resizable(False)
		self.set_icon_name(ICON)
		self.connect('destroy', self.close_application)
		#
		vbox0 = Gtk.VBox(spacing = 5)
		vbox0.set_border_width(5)
		self.get_content_area().add(vbox0)
		#
		notebook = Gtk.Notebook()
		vbox0.add(notebook)
		#
		frame = Gtk.Frame()
		notebook.append_page(frame,tab_label = Gtk.Label(_('Paginate')))
		#
		table = Gtk.Table(rows = 4, columns = 2, homogeneous = False)
		table.set_border_width(5)
		table.set_col_spacings(5)
		table.set_row_spacings(5)
		frame.add(table)
		#
		frame1 = Gtk.Frame()
		table.attach(frame1,0,1,0,1, xoptions = Gtk.AttachOptions.EXPAND, yoptions = Gtk.AttachOptions.SHRINK)
		self.scrolledwindow1 = Gtk.ScrolledWindow()
		self.scrolledwindow1.set_size_request(420,420)
		frame1.add(self.scrolledwindow1)
		#
		self.viewport1 = MiniView()
		self.scrolledwindow1.add(self.viewport1)
		#
		frame2 = Gtk.Frame()
		table.attach(frame2,1,2,0,1, xoptions = Gtk.AttachOptions.EXPAND, yoptions = Gtk.AttachOptions.SHRINK)
		scrolledwindow2 = Gtk.ScrolledWindow()
		scrolledwindow2.set_size_request(420,420)
		frame2.add(scrolledwindow2)
		#
		self.viewport2 = MiniView()
		scrolledwindow2.add(self.viewport2)
		self.viewport2.set_text('1/1')
		#
		self.scale=100
		
		#
		vertical_options = Gtk.ListStore(str,int)
		vertical_options.append([_('Top'),TOP])
		vertical_options.append([_('Middle'),MIDLE])
		vertical_options.append([_('Bottom'),BOTTOM])
		#
		horizontal_options = Gtk.ListStore(str,int)
		horizontal_options.append([_('Left'),LEFT])
		horizontal_options.append([_('Center'),CENTER])
		horizontal_options.append([_('Right'),RIGHT])
		#
		self.rbutton0  = Gtk.CheckButton(_('Overwrite original file?'))
		table.attach(self.rbutton0,0,2,1,2, xoptions = Gtk.AttachOptions.FILL, yoptions = Gtk.AttachOptions.SHRINK)
		# Font 2 3
		vbox1 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
		table.attach(vbox1,0,2,2,3, xoptions = Gtk.AttachOptions.FILL, yoptions = Gtk.AttachOptions.SHRINK)
		button_font = Gtk.Button(_('Select font'))
		button_font.connect('clicked',self.on_button_font_activated)
		vbox1.pack_start(button_font,False,False,0)
		button_color = Gtk.Button(_('Select color'))
		button_color.connect('clicked',self.on_button_color_activated)
		vbox1.pack_start(button_color,False,False,0)
		#
		label = Gtk.Label(_('Horizontal position')+':')
		table.attach(label,0,1,5,6, xoptions = Gtk.AttachOptions.FILL, yoptions = Gtk.AttachOptions.SHRINK)
		#
		self.horizontal = Gtk.ComboBox.new_with_model_and_entry(horizontal_options)
		self.horizontal.set_entry_text_column(0)
		self.horizontal.set_active(0)
		self.horizontal.connect('changed', self.on_value_changed)
		table.attach(self.horizontal,1,2,5,6, xoptions = Gtk.AttachOptions.FILL, yoptions = Gtk.AttachOptions.SHRINK)
		#
		label = Gtk.Label(_('Vertical position')+':')
		table.attach(label,0,1,6,7, xoptions = Gtk.AttachOptions.FILL, yoptions = Gtk.AttachOptions.SHRINK)
		#
		self.vertical = Gtk.ComboBox.new_with_model_and_entry(vertical_options)
		self.vertical.set_entry_text_column(0)
		self.vertical.set_active(0)
		self.vertical.connect('changed', self.on_value_changed)
		table.attach(self.vertical,1,2,6,7, xoptions = Gtk.AttachOptions.FILL, yoptions = Gtk.AttachOptions.SHRINK)		

		self.show_all()
		if filename != None:
			uri = "file://" + filename
			document = Poppler.Document.new_from_file(uri, None)
			if document.get_n_pages() > 0:
				self.viewport1.set_page(document.get_page(0))
				self.viewport2.set_page(document.get_page(0))
	def on_button_color_activated(self,widget):
		dialog = Gtk.ColorSelectionDialog(title=_('Select color'),flags=Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT)
		dialog.get_color_selection().set_current_color(Gdk.Color(self.viewport2.color[0]*65535,self.viewport2.color[1]*65535,self.viewport2.color[2]*65535))
		dialog.get_color_selection().set_current_alpha(self.viewport2.color[3]*65535)
		response = dialog.run()
		print(response)
		if response == -5:			
			color1 = dialog.get_color_selection().get_current_color()
			color2 = dialog.get_color_selection().get_current_alpha()
			self.viewport2.color = [color1.red/65535.0,color1.green/65535.0,color1.blue/65535.0,color2/65535.0]
			print(self.viewport2.color)
			self.update_preview()
		dialog.destroy()

	def on_button_font_activated(self,widget):
		dialog = Gtk.FontSelectionDialog(title=_('Select font'),flags=Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT)
		print(self.viewport2.font+' '+str(int(self.viewport2.size)))
		dialog.set_font_name(self.viewport2.font+' '+str(int(self.viewport2.size)))
		answer = dialog.run()
		if answer == -5:
			fs = dialog.get_font_selection()
			self.viewport2.font = ' '.join(fs.get_font_name().split()[:-1])
			self.viewport2.size = float(fs.get_font_name().split()[-1])
			self.update_preview()
		dialog.destroy()
	
	def get_color(self):
		return self.viewport2.color
		
	def get_font(self):
		return self.viewport2.font
		
	def get_size(self):
		return self.viewport2.size
		
	def on_value_changed(self,widget):
		self.update_preview()
		
	def get_image_filename(self):
		return self.entry.get_text()
		
	def get_horizontal_option(self):
		tree_iter = self.horizontal.get_active_iter()
		if tree_iter != None:
			model = self.horizontal.get_model()
			return model[tree_iter][1]
		return 0

	def get_vertical_option(self):
		tree_iter = self.vertical.get_active_iter()
		if tree_iter != None:
			model = self.vertical.get_model()
			return model[tree_iter][1]
		return 0
		
	def update_preview(self):
		self.viewport2.set_image_position_vertical(self.get_vertical_option())
		self.viewport2.set_image_position_horizontal(self.get_horizontal_option())
		self.viewport2.refresh()

	def close_application(self,widget):
		self.hide()			

class TextmarkDialog(Gtk.Dialog):
	def __init__(self,filename=None):
		Gtk.Dialog.__init__(self,_('Textmark'),None,Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,(Gtk.STOCK_OK, Gtk.ResponseType.ACCEPT,Gtk.STOCK_CANCEL,Gtk.ResponseType.CANCEL))
		self.set_size_request(500, 140)
		self.set_resizable(False)
		self.set_icon_name(ICON)
		self.connect('destroy', self.close_application)
		#
		vbox0 = Gtk.VBox(spacing = 5)
		vbox0.set_border_width(5)
		self.get_content_area().add(vbox0)
		#
		notebook = Gtk.Notebook()
		vbox0.add(notebook)
		#
		frame = Gtk.Frame()
		notebook.append_page(frame,tab_label = Gtk.Label(_('Textmark')))
		#
		table = Gtk.Table(rows = 4, columns = 2, homogeneous = False)
		table.set_border_width(5)
		table.set_col_spacings(5)
		table.set_row_spacings(5)
		frame.add(table)
		#
		frame1 = Gtk.Frame()
		table.attach(frame1,0,1,0,1, xoptions = Gtk.AttachOptions.EXPAND, yoptions = Gtk.AttachOptions.SHRINK)
		self.scrolledwindow1 = Gtk.ScrolledWindow()
		self.scrolledwindow1.set_size_request(420,420)
		frame1.add(self.scrolledwindow1)
		#
		self.viewport1 = MiniView()
		self.scrolledwindow1.add(self.viewport1)
		#
		frame2 = Gtk.Frame()
		table.attach(frame2,1,2,0,1, xoptions = Gtk.AttachOptions.EXPAND, yoptions = Gtk.AttachOptions.SHRINK)
		scrolledwindow2 = Gtk.ScrolledWindow()
		scrolledwindow2.set_size_request(420,420)
		frame2.add(scrolledwindow2)
		#
		self.viewport2 = MiniView()
		scrolledwindow2.add(self.viewport2)
		#
		self.scale=100
		
		#
		vertical_options = Gtk.ListStore(str,int)
		vertical_options.append([_('Top'),TOP])
		vertical_options.append([_('Middle'),MIDLE])
		vertical_options.append([_('Bottom'),BOTTOM])
		#
		horizontal_options = Gtk.ListStore(str,int)
		horizontal_options.append([_('Left'),LEFT])
		horizontal_options.append([_('Center'),CENTER])
		horizontal_options.append([_('Right'),RIGHT])
		#
		self.rbutton0  = Gtk.CheckButton(_('Overwrite original file?'))
		table.attach(self.rbutton0,0,2,1,2, xoptions = Gtk.AttachOptions.FILL, yoptions = Gtk.AttachOptions.SHRINK)
		# Font 2 3
		vbox1 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
		table.attach(vbox1,0,2,2,3, xoptions = Gtk.AttachOptions.FILL, yoptions = Gtk.AttachOptions.SHRINK)
		button_font = Gtk.Button(_('Select Font'))
		button_font.connect('clicked',self.on_button_font_activated)
		vbox1.pack_start(button_font,False,False,0)
		button_color = Gtk.Button(_('Select color'))
		button_color.connect('clicked',self.on_button_color_activated)
		vbox1.pack_start(button_color,False,False,0)
		# Color 3 4
		
		#
		vbox3 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
		table.attach(vbox3,0,2,4,5, xoptions = Gtk.AttachOptions.FILL, yoptions = Gtk.AttachOptions.SHRINK)
		label = Gtk.Label(_('Text')+':')
		vbox3.pack_start(label,False,False,0)
		self.entry = Gtk.Entry()
		self.entry.set_width_chars(50)
		#self.entry.set_sensitive(False)
		self.entry.connect('changed',self.on_entry_changed)
		vbox3.pack_start(self.entry,True,True,0)
		#
		label = Gtk.Label(_('Horizontal position')+':')
		table.attach(label,0,1,5,6, xoptions = Gtk.AttachOptions.FILL, yoptions = Gtk.AttachOptions.SHRINK)
		#
		self.horizontal = Gtk.ComboBox.new_with_model_and_entry(horizontal_options)
		self.horizontal.set_entry_text_column(0)
		self.horizontal.set_active(0)
		self.horizontal.connect('changed', self.on_value_changed)
		table.attach(self.horizontal,1,2,5,6, xoptions = Gtk.AttachOptions.FILL, yoptions = Gtk.AttachOptions.SHRINK)
		#
		label = Gtk.Label(_('Vertical position')+':')
		table.attach(label,0,1,6,7, xoptions = Gtk.AttachOptions.FILL, yoptions = Gtk.AttachOptions.SHRINK)
		#
		self.vertical = Gtk.ComboBox.new_with_model_and_entry(vertical_options)
		self.vertical.set_entry_text_column(0)
		self.vertical.set_active(0)
		self.vertical.connect('changed', self.on_value_changed)
		table.attach(self.vertical,1,2,6,7, xoptions = Gtk.AttachOptions.FILL, yoptions = Gtk.AttachOptions.SHRINK)		

		self.show_all()
		if filename != None:
			uri = "file://" + filename
			document = Poppler.Document.new_from_file(uri, None)
			if document.get_n_pages() > 0:
				self.viewport1.set_page(document.get_page(0))
				self.viewport2.set_page(document.get_page(0))
	def on_button_color_activated(self,widget):
		dialog = Gtk.ColorSelectionDialog(title=_('Select color'),flags=Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT)
		dialog.get_color_selection().set_current_color(Gdk.Color(self.viewport2.color[0]*65535,self.viewport2.color[1]*65535,self.viewport2.color[2]*65535))
		dialog.get_color_selection().set_current_alpha(self.viewport2.color[3]*65535)
		response = dialog.run()
		print(response)
		if response == -5:			
			color1 = dialog.get_color_selection().get_current_color()
			color2 = dialog.get_color_selection().get_current_alpha()
			self.viewport2.color = [color1.red/65535.0,color1.green/65535.0,color1.blue/65535.0,color2/65535.0]
			print(self.viewport2.color)
			self.update_preview()
		dialog.destroy()

	def on_button_font_activated(self,widget):
		dialog = Gtk.FontSelectionDialog(title=_('Select font'),flags=Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT)
		print(self.viewport2.font+' '+str(int(self.viewport2.size)))
		dialog.set_font_name(self.viewport2.font+' '+str(int(self.viewport2.size)))
		answer = dialog.run()
		if answer == -5:
			fs = dialog.get_font_selection()
			self.viewport2.font = ' '.join(fs.get_font_name().split()[:-1])
			self.viewport2.size = float(fs.get_font_name().split()[-1])
			self.update_preview()
		dialog.destroy()
	
	def get_color(self):
		return self.viewport2.color
		
	def get_font(self):
		return self.viewport2.font
		
	def get_size(self):
		return self.viewport2.size
		
	def get_text(self):
		return self.entry.get_text()
		
	def on_value_changed(self,widget):
		self.update_preview()
		
	def get_image_filename(self):
		return self.entry.get_text()
		
	def get_horizontal_option(self):
		tree_iter = self.horizontal.get_active_iter()
		if tree_iter != None:
			model = self.horizontal.get_model()
			return model[tree_iter][1]
		return 0

	def get_vertical_option(self):
		tree_iter = self.vertical.get_active_iter()
		if tree_iter != None:
			model = self.vertical.get_model()
			return model[tree_iter][1]
		return 0
		
	def on_entry_changed(self,widget):
		self.update_preview()

	def update_preview(self):
		text = self.entry.get_text()
		if len(text)>0:
			self.viewport2.set_text(self.entry.get_text())
			self.viewport2.set_image_position_vertical(self.get_vertical_option())
			self.viewport2.set_image_position_horizontal(self.get_horizontal_option())
			self.viewport2.refresh()

	def close_application(self,widget):
		self.hide()			
				
class WatermarkDialog(Gtk.Dialog):
	def __init__(self,filename=None):
		Gtk.Dialog.__init__(self,_('Watermark'),None,Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,(Gtk.STOCK_OK, Gtk.ResponseType.ACCEPT,Gtk.STOCK_CANCEL,Gtk.ResponseType.CANCEL))
		self.set_size_request(500, 140)
		self.set_resizable(False)
		self.set_icon_name(ICON)
		self.connect('destroy', self.close_application)
		#
		vbox0 = Gtk.VBox(spacing = 5)
		vbox0.set_border_width(5)
		self.get_content_area().add(vbox0)
		#
		notebook = Gtk.Notebook()
		vbox0.add(notebook)
		#
		frame = Gtk.Frame()
		notebook.append_page(frame,tab_label = Gtk.Label(_('Watermark')))
		#
		table = Gtk.Table(rows = 4, columns = 2, homogeneous = False)
		table.set_border_width(5)
		table.set_col_spacings(5)
		table.set_row_spacings(5)
		frame.add(table)
		#
		frame1 = Gtk.Frame()
		table.attach(frame1,0,1,0,1, xoptions = Gtk.AttachOptions.EXPAND, yoptions = Gtk.AttachOptions.SHRINK)
		self.scrolledwindow1 = Gtk.ScrolledWindow()
		self.scrolledwindow1.set_size_request(420,420)
		frame1.add(self.scrolledwindow1)
		#
		self.viewport1 = MiniView()
		self.scrolledwindow1.add(self.viewport1)
		#
		frame2 = Gtk.Frame()
		table.attach(frame2,1,2,0,1, xoptions = Gtk.AttachOptions.EXPAND, yoptions = Gtk.AttachOptions.SHRINK)
		scrolledwindow2 = Gtk.ScrolledWindow()
		scrolledwindow2.set_size_request(420,420)
		frame2.add(scrolledwindow2)
		#
		self.viewport2 = MiniView()
		scrolledwindow2.add(self.viewport2)
		#
		self.scale=100
		
		#
		vertical_options = Gtk.ListStore(str,int)
		vertical_options.append([_('Top'),TOP])
		vertical_options.append([_('Middle'),MIDLE])
		vertical_options.append([_('Bottom'),BOTTOM])
		#
		horizontal_options = Gtk.ListStore(str,int)
		horizontal_options.append([_('Left'),LEFT])
		horizontal_options.append([_('Center'),CENTER])
		horizontal_options.append([_('Right'),RIGHT])
		#
		self.rbutton0  = Gtk.CheckButton(_('Overwrite original file?'))
		table.attach(self.rbutton0,0,2,1,2, xoptions = Gtk.AttachOptions.FILL, yoptions = Gtk.AttachOptions.SHRINK)
		#
		vbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
		table.attach(vbox,0,2,2,3, xoptions = Gtk.AttachOptions.FILL, yoptions = Gtk.AttachOptions.SHRINK)
		label = Gtk.Label(_('Watermark')+':')
		vbox.pack_start(label,False,False,0)
		self.entry = Gtk.Entry()
		self.entry.set_width_chars(50)
		self.entry.set_sensitive(False)
		vbox.pack_start(self.entry,True,True,0)
		button = Gtk.Button(_('Choose File'))
		button.connect('clicked',self.on_button_clicked)
		vbox.pack_start(button,False,False,0)
		#
		label = Gtk.Label(_('Horizontal position')+':')
		table.attach(label,0,1,3,4, xoptions = Gtk.AttachOptions.FILL, yoptions = Gtk.AttachOptions.SHRINK)
		#
		self.horizontal = Gtk.ComboBox.new_with_model_and_entry(horizontal_options)
		self.horizontal.set_entry_text_column(0)
		self.horizontal.set_active(0)
		self.horizontal.connect('changed', self.on_value_changed)
		table.attach(self.horizontal,1,2,3,4, xoptions = Gtk.AttachOptions.FILL, yoptions = Gtk.AttachOptions.SHRINK)
		#
		label = Gtk.Label(_('Vertical position')+':')
		table.attach(label,0,1,4,5, xoptions = Gtk.AttachOptions.FILL, yoptions = Gtk.AttachOptions.SHRINK)
		#
		self.vertical = Gtk.ComboBox.new_with_model_and_entry(vertical_options)
		self.vertical.set_entry_text_column(0)
		self.vertical.set_active(0)
		self.vertical.connect('changed', self.on_value_changed)
		table.attach(self.vertical,1,2,4,5, xoptions = Gtk.AttachOptions.FILL, yoptions = Gtk.AttachOptions.SHRINK)		

		self.show_all()
		if filename != None:
			uri = "file://" + filename
			document = Poppler.Document.new_from_file(uri, None)
			if document.get_n_pages() > 0:
				self.viewport1.set_page(document.get_page(0))
				self.viewport2.set_page(document.get_page(0))
	
	def on_value_changed(self,widget):
		self.update_watermark()
		
	def get_image_filename(self):
		return self.entry.get_text()
		
	def get_horizontal_option(self):
		tree_iter = self.horizontal.get_active_iter()
		if tree_iter != None:
			model = self.horizontal.get_model()
			return model[tree_iter][1]
		return 0

	def get_vertical_option(self):
		tree_iter = self.vertical.get_active_iter()
		if tree_iter != None:
			model = self.vertical.get_model()
			return model[tree_iter][1]
		return 0
		
	def update_preview_cb(self,file_chooser, preview):
		filename = file_chooser.get_preview_filename()
		try:
			pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(filename, 128, 128)
			preview.set_from_pixbuf(pixbuf)
			have_preview = True
		except:
			have_preview = False
		file_chooser.set_preview_widget_active(have_preview)
		return
		
	def on_button_clicked(self,button):
		dialog = Gtk.FileChooserDialog(_('Please choose a file'), self,
            Gtk.FileChooserAction.OPEN,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
             Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
		dialog.set_default_response(Gtk.ResponseType.OK)
		dialog.set_select_multiple(False)
		dialog.set_current_folder(os.getenv('HOME'))
		filter_png = Gtk.FileFilter()
		filter_png.set_name(_('Png files'))
		filter_png.add_mime_type('image/png')
		dialog.add_filter(filter_png)
		preview = Gtk.Image()
		dialog.set_preview_widget(preview)
		dialog.connect('update-preview', self.update_preview_cb, preview)
		response = dialog.run()
		if response == Gtk.ResponseType.OK:
			self.entry.set_text(dialog.get_filename())
		dialog.destroy()
		####
		self.update_watermark()

	def update_watermark(self):
		file_watermark = self.entry.get_text()
		if file_watermark and os.path.exists(file_watermark):
			self.viewport2.set_image(file_watermark)
			self.viewport2.set_image_position_vertical(self.get_vertical_option())
			self.viewport2.set_image_position_horizontal(self.get_horizontal_option())

	def close_application(self,widget):
		self.hide()			

class FlipDialog(Gtk.Dialog):
	def __init__(self,title,filename=None):
		Gtk.Dialog.__init__(self,title,None,Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,(Gtk.STOCK_OK, Gtk.ResponseType.ACCEPT,Gtk.STOCK_CANCEL,Gtk.ResponseType.CANCEL))
		self.set_default_size(800,400)
		self.set_resizable(True)
		self.connect('destroy', self.close)
		#
		vbox = Gtk.VBox(spacing = 5)
		vbox.set_border_width(5)
		self.get_content_area().add(vbox)
		#
		frame = Gtk.Frame()
		vbox.pack_start(frame,True,True,0)
		#
		table = Gtk.Table(rows = 2, columns = 3, homogeneous = False)
		table.set_border_width(5)
		table.set_col_spacings(5)
		table.set_row_spacings(5)
		frame.add(table)		
		#
		frame1 = Gtk.Frame()
		table.attach(frame1,0,1,0,1, xoptions = Gtk.AttachOptions.EXPAND, yoptions = Gtk.AttachOptions.SHRINK)
		self.scrolledwindow1 = Gtk.ScrolledWindow()
		self.scrolledwindow1.set_size_request(420,420)
		self.connect('key-release-event',self.on_key_release_event)		
		frame1.add(self.scrolledwindow1)
		#
		self.viewport1 = MiniView()
		self.scrolledwindow1.add(self.viewport1)
		#
		frame2 = Gtk.Frame()
		table.attach(frame2,1,2,0,1, xoptions = Gtk.AttachOptions.EXPAND, yoptions = Gtk.AttachOptions.SHRINK)
		scrolledwindow2 = Gtk.ScrolledWindow()
		scrolledwindow2.set_size_request(420,420)
		self.connect('key-release-event',self.on_key_release_event)
		frame2.add(scrolledwindow2)
		#
		self.viewport2 = MiniView()
		scrolledwindow2.add(self.viewport2)
		#
		self.scale=100
		#
		#
		self.rbutton0  = Gtk.CheckButton(_('Overwrite original file?'))
		table.attach(self.rbutton0,0,2,1,2, xoptions = Gtk.AttachOptions.FILL, yoptions = Gtk.AttachOptions.SHRINK)		
		#
		table.attach(Gtk.Label(_('Flip vertical')),0,1,2,3, xoptions = Gtk.AttachOptions.SHRINK, yoptions = Gtk.AttachOptions.SHRINK)		
		self.switch1 = Gtk.Switch()
		self.switch1.set_name('switch1')
		self.switch1.connect("notify::active", self.slider_on_value_changed)		
		hbox1 = Gtk.HBox()
		hbox1.pack_start(self.switch1,0,0,0)
		table.attach(hbox1,1,2,2,3, xoptions = Gtk.AttachOptions.FILL, yoptions = Gtk.AttachOptions.SHRINK)		
		#
		table.attach(Gtk.Label(_('Flip horizontal')),0,1,3,4, xoptions = Gtk.AttachOptions.SHRINK, yoptions = Gtk.AttachOptions.SHRINK)		
		self.switch2 = Gtk.Switch()
		self.switch2.set_name('switch2')
		self.switch2.connect("notify::active", self.slider_on_value_changed)
		hbox2 = Gtk.HBox()
		hbox2.pack_start(self.switch2,0,0,0)
		table.attach(hbox2,1,2,3,4, xoptions = Gtk.AttachOptions.FILL, yoptions = Gtk.AttachOptions.SHRINK)		
		#
		table.attach(Gtk.Label(_('Rotate')),0,1,4,5, xoptions = Gtk.AttachOptions.FILL, yoptions = Gtk.AttachOptions.SHRINK)		
		table1 = Gtk.Table(rows = 1, columns = 4, homogeneous = False)
		table1.set_border_width(5)
		table1.set_col_spacings(5)
		table1.set_row_spacings(5)
		table.attach(table1,1,2,4,5, xoptions = Gtk.AttachOptions.FILL, yoptions = Gtk.AttachOptions.SHRINK)		
		self.rbutton1 = Gtk.RadioButton.new_with_label_from_widget(None,'0')
		self.rbutton1.set_name('0')
		self.rbutton1.connect("notify::active", self.slider_on_value_changed)
		table1.attach(self.rbutton1,0,1,0,1, xoptions = Gtk.AttachOptions.EXPAND, yoptions = Gtk.AttachOptions.SHRINK)
		self.rbutton2 = Gtk.RadioButton.new_with_label_from_widget(self.rbutton1,'90')		
		self.rbutton2.set_name('90')
		self.rbutton2.connect("notify::active", self.slider_on_value_changed)
		table1.attach(self.rbutton2,1,2,0,1, xoptions = Gtk.AttachOptions.EXPAND, yoptions = Gtk.AttachOptions.SHRINK)
		self.rbutton3 = Gtk.RadioButton.new_with_label_from_widget(self.rbutton1,'180')
		self.rbutton3.set_name('180')
		self.rbutton3.connect("notify::active", self.slider_on_value_changed)
		table1.attach(self.rbutton3,2,3,0,1, xoptions = Gtk.AttachOptions.EXPAND, yoptions = Gtk.AttachOptions.SHRINK)
		self.rbutton4 = Gtk.RadioButton.new_with_label_from_widget(self.rbutton1,'270')
		self.rbutton4.set_name('270')
		self.rbutton4.connect("notify::active", self.slider_on_value_changed)
		table1.attach(self.rbutton4,3,4,0,1, xoptions = Gtk.AttachOptions.EXPAND, yoptions = Gtk.AttachOptions.SHRINK)
		#
		if filename != None:
			uri = "file://" + filename
			document = Poppler.Document.new_from_file(uri, None)
			if document.get_n_pages() > 0:
				self.viewport1.set_page(document.get_page(0))
				self.viewport2.set_page(document.get_page(0))
		#
		print(1)
		self.show_all()
		#
	def slider_on_value_changed(self,widget,calue):
		print(widget.get_name())
		if widget.get_name() == 'switch1':
			self.viewport2.set_flip_vertical(self.switch1.get_active())
		elif widget.get_name() == 'switch2':
			self.viewport2.set_flip_horizontal(self.switch2.get_active())
		elif widget.get_name() == '0':
			self.viewport2.set_rotation_angle(0.0)
		elif widget.get_name() == '90':
			self.viewport2.set_rotation_angle(1.0)
		elif widget.get_name() == '180':
			self.viewport2.set_rotation_angle(2.0)
		elif widget.get_name() == '270':
			self.viewport2.set_rotation_angle(3.0)
		
	def on_key_release_event(self,widget,event):
		print((event.keyval))
		if event.keyval == 65451 or event.keyval == 43:
			self.scale=self.scale*1.1
		elif event.keyval == 65453 or event.keyval == 45:
			self.scale=self.scale*.9
		elif event.keyval == 65456 or event.keyval == 48:
			factor_w = float(self.scrolledwindow1.get_allocation().width)/float(self.pixbuf1.get_width())
			factor_h = float(self.scrolledwindow1.get_allocation().height)/float(self.pixbuf1.get_height())
			if factor_w < factor_h:
				factor = factor_w
			else:
				factor = factor_h
			self.scale = int(factor*100)
			w=int(self.pixbuf1.get_width()*factor)
			h=int(self.pixbuf1.get_height()*factor)
			#
			self.image1.set_from_pixbuf(self.pixbuf1.scale_simple(w,h,GdkPixbuf.InterpType.BILINEAR))
			self.image2.set_from_pixbuf(self.pixbuf2.scale_simple(w,h,GdkPixbuf.InterpType.BILINEAR))		
		elif event.keyval == 65457 or event.keyval == 49:
			self.scale = 100
		if self.image1:
			w=int(self.pixbuf1.get_width()*self.scale/100)
			h=int(self.pixbuf1.get_height()*self.scale/100)
			#
			self.image1.set_from_pixbuf(self.pixbuf1.scale_simple(w,h,GdkPixbuf.InterpType.BILINEAR))
			self.image2.set_from_pixbuf(self.pixbuf2.scale_simple(w,h,GdkPixbuf.InterpType.BILINEAR))

	def close(self,widget):
		self.destroy()
		
class JoinPdfsDialog(Gtk.Dialog):
	def __init__(self,title,files):
		Gtk.Dialog.__init__(self,title,None,Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,(Gtk.STOCK_OK, Gtk.ResponseType.ACCEPT,Gtk.STOCK_CANCEL,Gtk.ResponseType.CANCEL))
		self.set_size_request(450, 300)
		self.set_resizable(False)
		self.set_icon_name(ICON)
		self.connect('destroy', self.close_application)
		#
		vbox0 = Gtk.VBox(spacing = 5)
		vbox0.set_border_width(5)
		self.get_content_area().add(vbox0)
		#
		hbox = Gtk.HBox()
		vbox0.pack_start(hbox,True,True,0)
		#
		scrolledwindow = Gtk.ScrolledWindow()
		scrolledwindow.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
		scrolledwindow.set_shadow_type(Gtk.ShadowType.ETCHED_OUT)
		scrolledwindow.set_size_request(450,300)
		hbox.pack_start(scrolledwindow,True,True,0)
		#
		# id, text, image
		self.store = Gtk.ListStore(str)
		self.treeview = Gtk.TreeView(model=self.store)	
		self.treeview.append_column(Gtk.TreeViewColumn(_('Pdf file'), Gtk.CellRendererText(), text=0))		
		scrolledwindow.add(self.treeview)
		#
		vbox2 = Gtk.VBox(spacing = 0)
		vbox2.set_border_width(5)
		hbox.pack_start(vbox2,False,False,0)
		#
		self.button1 = Gtk.Button()
		self.button1.set_size_request(40,40)
		self.button1.set_tooltip_text(_('Up'))	
		self.button1.set_image(Gtk.Image.new_from_stock(Gtk.STOCK_GO_UP,Gtk.IconSize.BUTTON))
		self.button1.connect('clicked',self.on_button_up_clicked)
		vbox2.pack_start(self.button1,False,False,0)
		#
		self.button2 = Gtk.Button()
		self.button2.set_size_request(40,40)
		self.button2.set_tooltip_text(_('Down'))	
		self.button2.set_image(Gtk.Image.new_from_stock(Gtk.STOCK_GO_DOWN,Gtk.IconSize.BUTTON))
		self.button2.connect('clicked',self.on_button_down_clicked)
		vbox2.pack_start(self.button2,False,False,0)
		#
		self.button3 = Gtk.Button()
		self.button3.set_size_request(40,40)
		self.button3.set_tooltip_text(_('Add'))		
		self.button3.set_image(Gtk.Image.new_from_stock(Gtk.STOCK_ADD,Gtk.IconSize.BUTTON))
		self.button3.connect('clicked',self.on_button_add_clicked)
		vbox2.pack_start(self.button3,False,False,0)
		#
		self.button4 = Gtk.Button()
		self.button4.set_size_request(40,40)
		self.button4.set_tooltip_text(_('Remove'))		
		self.button4.set_image(Gtk.Image.new_from_stock(Gtk.STOCK_REMOVE,Gtk.IconSize.BUTTON))
		self.button4.connect('clicked',self.on_button_remove_clicked)
		vbox2.pack_start(self.button4,False,False,0)
		#
		for afile in files:
			self.store.append([afile])
		#
		self.show_all()	
		
	def on_button_up_clicked(self,widget):
		selection = self.treeview.get_selection()
		if selection.count_selected_rows()>0:
			model,iter = selection.get_selected()
			treepath = model.get_path(iter)
			path = int(str(treepath))
			if path > 0:
				previous_path = Gtk.TreePath.new_from_string(str(path - 1))
				previous_iter = model.get_iter(previous_path)
				model.swap(iter,previous_iter)
				
	def on_button_down_clicked(self,widget):
		selection = self.treeview.get_selection()
		if selection.count_selected_rows()>0:
			model,iter = selection.get_selected()
			treepath = model.get_path(iter)
			path = int(str(treepath))
			if path < len(model)-1:
				next_path = Gtk.TreePath.new_from_string(str(path + 1))
				next_iter = model.get_iter(next_path)
				model.swap(iter,next_iter)

	def on_button_add_clicked(self,widget):
		selection = self.treeview.get_selection()
		if selection.count_selected_rows()>0:
			model,iter = selection.get_selected()
			treepath = model.get_path(iter)
			position = int(str(treepath))
			dialog = Gtk.FileChooserDialog(_('Select one or more pdf files'),
											self,
										   Gtk.FileChooserAction.OPEN,
										   (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
											Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
			dialog.set_default_response(Gtk.ResponseType.OK)
			dialog.set_select_multiple(True)
			dialog.set_current_folder(os.getenv('HOME'))
			filter = Gtk.FileFilter()
			filter.set_name(_('Pdf files'))
			filter.add_mime_type('application/pdf')
			filter.add_pattern('*.pdf')
			dialog.add_filter(filter)
			preview = Gtk.Image()
			response = dialog.run()
			if response == Gtk.ResponseType.OK:
				filenames = dialog.get_filenames()
				if len(filenames)>0:
					for i,filename in enumerate(filenames):
						model.insert(position+i+1,[filename])
			dialog.destroy()			


	def on_button_remove_clicked(self,widget):
		selection = self.treeview.get_selection()
		if selection.count_selected_rows()>0:
			model,iter = selection.get_selected()
			model.remove(iter)

	def close_application(self,widget):
		self.hide()

	def get_pdf_files(self):
		files = []
		iter = self.store.get_iter_first()
		while(iter):
			files.append(self.store.get_value(iter,0))
			iter = self.store.iter_next(iter)
		return files
			

class SelectPagesRotateDialog(Gtk.Dialog):
	def __init__(self, title, last_page):
		Gtk.Dialog.__init__(self,title,None,Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,(Gtk.STOCK_OK, Gtk.ResponseType.ACCEPT,Gtk.STOCK_CANCEL,Gtk.ResponseType.CANCEL))
		self.set_size_request(300, 140)
		self.set_resizable(False)
		self.set_icon_name(ICON)
		self.connect('destroy', self.close_application)
		#
		vbox0 = Gtk.VBox(spacing = 5)
		vbox0.set_border_width(5)
		self.get_content_area().add(vbox0)
		#
		notebook = Gtk.Notebook()
		vbox0.add(notebook)
		#
		frame1 = Gtk.Frame()
		notebook.append_page(frame1,tab_label = Gtk.Label(_('Select Pages')))
		#
		table1 = Gtk.Table(rows = 3, columns = 3, homogeneous = False)
		table1.set_border_width(5)
		table1.set_col_spacings(5)
		table1.set_row_spacings(5)
		frame1.add(table1)
		#
		label1 = Gtk.Label(_('Pages')+':')
		label1.set_tooltip_text(_('Type page number and/or page\nranges separated by commas\ncounting from start of the\ndocument ej. 1,4,6-9'))
		label1.set_alignment(0,.5)
		table1.attach(label1,0,1,0,1, xoptions = Gtk.AttachOptions.FILL, yoptions = Gtk.AttachOptions.SHRINK)
		#
		self.entry1 = Gtk.Entry()
		self.entry1.set_tooltip_text(_('Type page number and/or page\nranges separated by commas\ncounting from start of the\ndocument ej. 1,4,6-9'))
		table1.attach(self.entry1,1,3,0,1, xoptions = Gtk.AttachOptions.EXPAND, yoptions = Gtk.AttachOptions.SHRINK)
		#
		self.rbutton1 = Gtk.RadioButton.new_from_widget(None)
		self.rbutton1.add(Gtk.Image.new_from_icon_name('object-rotate-left',Gtk.IconSize.BUTTON))
		table1.attach(self.rbutton1,0,1,2,3, xoptions = Gtk.AttachOptions.EXPAND, yoptions = Gtk.AttachOptions.SHRINK)
		self.rbutton2 = Gtk.RadioButton.new_from_widget(self.rbutton1)
		self.rbutton2.add(Gtk.Image.new_from_icon_name('object-rotate-right',Gtk.IconSize.BUTTON))
		table1.attach(self.rbutton2,1,2,2,3, xoptions = Gtk.AttachOptions.EXPAND, yoptions = Gtk.AttachOptions.SHRINK)
		self.rbutton3 = Gtk.RadioButton.new_from_widget(self.rbutton1)
		self.rbutton3.add(Gtk.Image.new_from_icon_name('object-flip-vertical',Gtk.IconSize.BUTTON))
		table1.attach(self.rbutton3,2,3,2,3, xoptions = Gtk.AttachOptions.EXPAND, yoptions = Gtk.AttachOptions.SHRINK)
		self.show_all()
	def close_application(self,widget):
		self.hide()
		
class SelectPagesDialog(Gtk.Dialog):
	def __init__(self, title, last_page):
		Gtk.Dialog.__init__(self,title,None,Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,(Gtk.STOCK_OK, Gtk.ResponseType.ACCEPT,Gtk.STOCK_CANCEL,Gtk.ResponseType.CANCEL))
		self.set_size_request(300, 120)
		self.set_resizable(False)
		self.set_icon_name(ICON)
		self.connect('destroy', self.close_application)
		#
		vbox0 = Gtk.VBox(spacing = 5)
		vbox0.set_border_width(5)
		self.get_content_area().add(vbox0)
		#
		notebook = Gtk.Notebook()
		vbox0.add(notebook)
		#
		frame1 = Gtk.Frame()
		notebook.append_page(frame1,tab_label = Gtk.Label(_('Select Pages')))
		#
		table1 = Gtk.Table(rows = 3, columns = 3, homogeneous = False)
		table1.set_border_width(5)
		table1.set_col_spacings(5)
		table1.set_row_spacings(5)
		frame1.add(table1)
		#
		label1 = Gtk.Label(_('Pages')+':')
		label1.set_tooltip_text(_('Type page number and/or page\nranges separated by commas\ncounting from start of the\ndocument ej. 1,4,6-9'))
		label1.set_alignment(0,.5)
		table1.attach(label1,0,1,0,1, xoptions = Gtk.AttachOptions.FILL, yoptions = Gtk.AttachOptions.SHRINK)
		#
		self.entry1 = Gtk.Entry()
		self.entry1.set_tooltip_text(_('Type page number and/or page\nranges separated by commas\ncounting from start of the\ndocument ej. 1,4,6-9'))
		table1.attach(self.entry1,1,3,0,1, xoptions = Gtk.AttachOptions.EXPAND, yoptions = Gtk.AttachOptions.SHRINK)
		#
		self.show_all()
	def close_application(self,widget):
		self.hide()

class ConvertDialog(Gtk.Dialog):
	def __init__(self):
		Gtk.Dialog.__init__(self,_('Convert to'),None,Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,(Gtk.STOCK_OK, Gtk.ResponseType.ACCEPT,Gtk.STOCK_CANCEL,Gtk.ResponseType.CANCEL))
		self.set_size_request(300, 140)
		self.set_resizable(False)
		self.set_icon_name(ICON)
		self.connect('destroy', self.close_application)
		#
		vbox0 = Gtk.VBox(spacing = 5)
		vbox0.set_border_width(5)
		self.get_content_area().add(vbox0)
		#
		notebook = Gtk.Notebook()
		vbox0.add(notebook)
		#
		frame1 = Gtk.Frame()
		notebook.append_page(frame1,tab_label = Gtk.Label(_('Convert to')))
		#
		table1 = Gtk.Table(rows = 1, columns = 2, homogeneous = False)
		table1.set_border_width(5)
		table1.set_col_spacings(5)
		table1.set_row_spacings(5)
		frame1.add(table1)
		#
		options = Gtk.ListStore(str)
		for extension in EXTENSIONS:
			options.append([extension[1:]])
		label = Gtk.Label(_('Convert to')+':')
		table1.attach(label,0,1,0,1, xoptions = Gtk.AttachOptions.EXPAND, yoptions = Gtk.AttachOptions.SHRINK)
		#
		self.convert_to = Gtk.ComboBox.new_with_model_and_entry(options)
		self.convert_to.set_entry_text_column(0)
		self.convert_to.set_active(0)
		table1.attach(self.convert_to,1,2,0,1, xoptions = Gtk.AttachOptions.EXPAND, yoptions = Gtk.AttachOptions.SHRINK)
		#
		self.show_all()
		
	def get_convert_to(self):
		tree_iter = self.convert_to.get_active_iter()
		if tree_iter != None:
			model = self.convert_to.get_model()
			return model[tree_iter][0]
		return 'png'
		
	def close_application(self,widget):
		self.hide()

	
class CombineDialog(Gtk.Dialog):
	def __init__(self, title):
		Gtk.Dialog.__init__(self,title,None,Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,(Gtk.STOCK_OK, Gtk.ResponseType.ACCEPT,Gtk.STOCK_CANCEL,Gtk.ResponseType.CANCEL))
		self.set_size_request(350, 150)
		self.set_resizable(False)
		self.set_icon_name(ICON)
		self.connect('destroy', self.close_application)
		#
		vbox0 = Gtk.VBox(spacing = 5)
		vbox0.set_border_width(5)
		self.get_content_area().add(vbox0)
		#
		notebook = Gtk.Notebook()
		vbox0.add(notebook)
		#
		frame1 = Gtk.Frame()
		notebook.append_page(frame1,tab_label = Gtk.Label(_('Pages')))
		#
		table1 = Gtk.Table(rows = 5, columns = 4, homogeneous = False)
		table1.set_border_width(5)
		table1.set_col_spacings(5)
		table1.set_row_spacings(5)
		frame1.add(table1)
		#
		label1 = Gtk.Label(_('Paper size')+':')
		label1.set_tooltip_text(_('Select the size of the output file'))
		label1.set_alignment(0,.5)
		table1.attach(label1,0,1,0,1, xoptions = Gtk.AttachOptions.FILL, yoptions = Gtk.AttachOptions.SHRINK)
		#
		label2 = Gtk.Label(_('Orientation')+':')
		label2.set_tooltip_text(_('Select the orientation of the page'))
		label2.set_alignment(0,.5)
		table1.attach(label2,0,1,1,2, xoptions = Gtk.AttachOptions.FILL, yoptions = Gtk.AttachOptions.SHRINK)
		#
		label3 = Gtk.Label(_('Pages in Page')+':')
		label3.set_tooltip_text(_('Select how many pages in a page'))
		label3.set_alignment(0,.5)
		table1.attach(label3,0,1,2,3, xoptions = Gtk.AttachOptions.FILL, yoptions = Gtk.AttachOptions.SHRINK)
		#
		label4 = Gtk.Label(_('by'))
		label4.set_tooltip_text(_('rows by columns'))
		label4.set_alignment(.5,.5)
		table1.attach(label4,2,3,2,3, xoptions = Gtk.AttachOptions.FILL, yoptions = Gtk.AttachOptions.SHRINK)		
		#
		label5 = Gtk.Label(_('Sort')+':')
		label5.set_tooltip_text(_('Select the combination sort'))
		label5.set_alignment(0,.5)
		table1.attach(label5,0,1,3,4, xoptions = Gtk.AttachOptions.FILL, yoptions = Gtk.AttachOptions.SHRINK)
		#
		label6 = Gtk.Label(_('Set the margin')+':')
		label6.set_tooltip_text(_('The margin to the page in mm'))
		label6.set_alignment(0,.5)
		table1.attach(label6,0,1,4,5, xoptions = Gtk.AttachOptions.FILL, yoptions = Gtk.AttachOptions.SHRINK)
		#
		liststore = Gtk.ListStore(str, float, float)
		liststore.append([_('A0'),2383.9,3370.4])
		liststore.append([_('A1'),1683.8,2383.9])
		liststore.append([_('A2'),1190.6,1683.8])
		liststore.append([_('A3'),841.9,1190.6])
		liststore.append([_('A4'),595.3,841.9])
		liststore.append([_('A5'),419.5,595.3])
		liststore.append([_('A6'),297.6,419.5])
		liststore.append([_('A7'),209.8,297.6])
		liststore.append([_('A8'),147.4,209.8])
		liststore.append([_('A9'),104.9,147.4])
		liststore.append([_('A10'),73.7,104.9])
		liststore.append([_('B0'),2834.6,73.7])
		liststore.append([_('B1'),2004.1,2834.6])
		liststore.append([_('B2'),1417.3,2004.1])
		liststore.append([_('B3'),1000.6,1417.3])
		liststore.append([_('B4'),708.7,1000.6])
		liststore.append([_('B5'),498.9,708.7])
		liststore.append([_('B6'),354.3,498.9])
		liststore.append([_('B7'),249.4,354.3])
		liststore.append([_('B8'),175.7,249.4])
		liststore.append([_('B9'),124.7,175.7])
		liststore.append([_('B10'),87.9,124.7])
		liststore.append([_('Letter (8 1/2x11)'),612.0,792.0])
		liststore.append([_('Note (8 1/2x11)'),612.0,792.0])
		liststore.append([_('Legal (8 1/2x14)'),612.0,1008.0])
		liststore.append([_('Executive (8 1/4x10 1/2)'),522.0,756.0])
		liststore.append([_('Halfetter (5 1/2x8 1/2)'),396.0,612.0])
		liststore.append([_('Halfexecutive (5 1/4x7 1/4)'),378.0,522.0])
		liststore.append([_('11x17 (11x17)'),792.0,1224.0])
		liststore.append([_('Statement (5 1/2x8 1/2)'),396.0,612.0])
		liststore.append([_('Folio (8 1/2x13)'),612.0,936.0])
		liststore.append([_('10x14 (10x14)'),720.0,1008.0])
		liststore.append([_('Ledger (17x11)'),1224.0,792.0])
		liststore.append([_('Tabloid (11x17)'),792.0,1224.0])
		self.entry1 = Gtk.ComboBox.new_with_model(model=liststore)
		renderer_text = Gtk.CellRendererText()
		self.entry1.pack_start(renderer_text, True)
		self.entry1.add_attribute(renderer_text, "text", 0)
		self.entry1.set_active(0)
		table1.attach(self.entry1,1,4,0,1, xoptions = Gtk.AttachOptions.FILL, yoptions = Gtk.AttachOptions.SHRINK)
		#
		liststore = Gtk.ListStore(str)
		liststore.append([_('Vertical')])
		liststore.append([_('Horizontal')])
		self.entry2 = Gtk.ComboBox.new_with_model(model=liststore)
		renderer_text = Gtk.CellRendererText()
		self.entry2.pack_start(renderer_text, True)
		self.entry2.add_attribute(renderer_text, "text", 0)
		self.entry2.set_active(0)
		table1.attach(self.entry2,1,4,1,2, xoptions = Gtk.AttachOptions.FILL, yoptions = Gtk.AttachOptions.SHRINK)
		#
		self.entry3 = Gtk.SpinButton()
		self.entry3.set_adjustment(Gtk.Adjustment(1,1,100,1,10,10))
		self.entry3.set_value(1)
		table1.attach(self.entry3,1,2,2,3, xoptions = Gtk.AttachOptions.FILL, yoptions = Gtk.AttachOptions.SHRINK)
		#
		self.entry4 = Gtk.SpinButton()
		self.entry4.set_adjustment(Gtk.Adjustment(1,1,100,1,10,10))
		self.entry4.set_value(2)
		table1.attach(self.entry4,3,4,2,3, xoptions = Gtk.AttachOptions.FILL, yoptions = Gtk.AttachOptions.SHRINK)
		#
		liststore = Gtk.ListStore(str)
		liststore.append([_('By rows')])
		liststore.append([_('By columns')])
		self.entry5 = Gtk.ComboBox.new_with_model(model=liststore)
		renderer_text = Gtk.CellRendererText()
		self.entry5.pack_start(renderer_text, True)
		self.entry5.add_attribute(renderer_text, "text", 0)
		self.entry5.set_active(0)
		table1.attach(self.entry5,1,4,3,4, xoptions = Gtk.AttachOptions.FILL, yoptions = Gtk.AttachOptions.SHRINK)
		#
		self.entry6 = Gtk.SpinButton()
		self.entry6.set_adjustment(Gtk.Adjustment(0,0,100,1,10,10))
		self.entry6.set_value(0)
		table1.attach(self.entry6,1,4,4,5, xoptions = Gtk.AttachOptions.FILL, yoptions = Gtk.AttachOptions.SHRINK)
		#
		self.show_all()

	def get_size(self):
		tree_iter = self.entry1.get_active_iter()
		if tree_iter != None:
			model = self.entry1.get_model()
			w = model[tree_iter][1]
			h = model[tree_iter][2]
			return w,h
		return None

	def is_vertical(self):
		tree_iter = self.entry2.get_active_iter()
		if tree_iter != None:
			model = self.entry2.get_model()
			vertical = model[tree_iter][0]
			if vertical == _('Vertical'):
				return True
		return False

	def get_rows(self):
		return self.entry3.get_value()

	def get_columns(self):
		return self.entry4.get_value()
	
	def is_sort_by_rows(self):
		tree_iter = self.entry5.get_active_iter()
		if tree_iter != None:
			model = self.entry5.get_model()
			vertical = model[tree_iter][0]
			if vertical ==_('By rows'):
				return True
		return False
	def get_margin(self):
		return self.entry6.get_value()
		
	def close_application(self,widget):
		self.hide()	
		
class ResizeDialog(Gtk.Dialog):
	def __init__(self, title):
		Gtk.Dialog.__init__(self,title,None,Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,(Gtk.STOCK_OK, Gtk.ResponseType.ACCEPT,Gtk.STOCK_CANCEL,Gtk.ResponseType.CANCEL))
		self.set_size_request(350, 150)
		self.set_resizable(False)
		self.set_icon_name(ICON)
		self.connect('destroy', self.close_application)
		#
		vbox0 = Gtk.VBox(spacing = 5)
		vbox0.set_border_width(5)
		self.get_content_area().add(vbox0)
		#
		notebook = Gtk.Notebook()
		vbox0.add(notebook)
		#
		frame1 = Gtk.Frame()
		notebook.append_page(frame1,tab_label = Gtk.Label(_('Pages')))
		#
		table1 = Gtk.Table(rows = 5, columns = 4, homogeneous = False)
		table1.set_border_width(5)
		table1.set_col_spacings(5)
		table1.set_row_spacings(5)
		frame1.add(table1)
		#
		label1 = Gtk.Label(_('Paper size')+':')
		label1.set_tooltip_text(_('Select the size of the output file'))
		label1.set_alignment(0,.5)
		table1.attach(label1,0,1,0,1, xoptions = Gtk.AttachOptions.FILL, yoptions = Gtk.AttachOptions.SHRINK)
		#
		label2 = Gtk.Label(_('Orientation')+':')
		label2.set_tooltip_text(_('Select the orientation of the page'))
		label2.set_alignment(0,.5)
		table1.attach(label2,0,1,1,2, xoptions = Gtk.AttachOptions.FILL, yoptions = Gtk.AttachOptions.SHRINK)
		#
		liststore = Gtk.ListStore(str, float, float)
		liststore.append([_('A0'),2383.9,3370.4])
		liststore.append([_('A1'),1683.8,2383.9])
		liststore.append([_('A2'),1190.6,1683.8])
		liststore.append([_('A3'),841.9,1190.6])
		liststore.append([_('A4'),595.3,841.9])
		liststore.append([_('A5'),419.5,595.3])
		liststore.append([_('A6'),297.6,419.5])
		liststore.append([_('A7'),209.8,297.6])
		liststore.append([_('A8'),147.4,209.8])
		liststore.append([_('A9'),104.9,147.4])
		liststore.append([_('A10'),73.7,104.9])
		liststore.append([_('B0'),2834.6,73.7])
		liststore.append([_('B1'),2004.1,2834.6])
		liststore.append([_('B2'),1417.3,2004.1])
		liststore.append([_('B3'),1000.6,1417.3])
		liststore.append([_('B4'),708.7,1000.6])
		liststore.append([_('B5'),498.9,708.7])
		liststore.append([_('B6'),354.3,498.9])
		liststore.append([_('B7'),249.4,354.3])
		liststore.append([_('B8'),175.7,249.4])
		liststore.append([_('B9'),124.7,175.7])
		liststore.append([_('B10'),87.9,124.7])
		liststore.append([_('Letter (8 1/2x11)'),612.0,792.0])
		liststore.append([_('Note (8 1/2x11)'),612.0,792.0])
		liststore.append([_('Legal (8 1/2x14)'),612.0,1008.0])
		liststore.append([_('Executive (8 1/4x10 1/2)'),522.0,756.0])
		liststore.append([_('Halfetter (5 1/2x8 1/2)'),396.0,612.0])
		liststore.append([_('Halfexecutive (5 1/4x7 1/4)'),378.0,522.0])
		liststore.append([_('11x17 (11x17)'),792.0,1224.0])
		liststore.append([_('Statement (5 1/2x8 1/2)'),396.0,612.0])
		liststore.append([_('Folio (8 1/2x13)'),612.0,936.0])
		liststore.append([_('10x14 (10x14)'),720.0,1008.0])
		liststore.append([_('Ledger (17x11)'),1224.0,792.0])
		liststore.append([_('Tabloid (11x17)'),792.0,1224.0])
		self.entry1 = Gtk.ComboBox.new_with_model(model=liststore)
		renderer_text = Gtk.CellRendererText()
		self.entry1.pack_start(renderer_text, True)
		self.entry1.add_attribute(renderer_text, "text", 0)
		self.entry1.set_active(0)
		table1.attach(self.entry1,1,4,0,1, xoptions = Gtk.AttachOptions.FILL, yoptions = Gtk.AttachOptions.SHRINK)
		#
		liststore = Gtk.ListStore(str)
		liststore.append([_('Vertical')])
		liststore.append([_('Horizontal')])
		self.entry2 = Gtk.ComboBox.new_with_model(model=liststore)
		renderer_text = Gtk.CellRendererText()
		self.entry2.pack_start(renderer_text, True)
		self.entry2.add_attribute(renderer_text, "text", 0)
		self.entry2.set_active(0)
		table1.attach(self.entry2,1,4,1,2, xoptions = Gtk.AttachOptions.FILL, yoptions = Gtk.AttachOptions.SHRINK)
		#
		self.show_all()

	def get_size(self):
		tree_iter = self.entry1.get_active_iter()
		if tree_iter != None:
			model = self.entry1.get_model()
			w = model[tree_iter][1]
			h = model[tree_iter][2]
			return w,h
		return None

	def is_vertical(self):
		tree_iter = self.entry2.get_active_iter()
		if tree_iter != None:
			model = self.entry2.get_model()
			vertical = model[tree_iter][0]
			if vertical == _('Vertical'):
				return True
		return False
	
	def close_application(self,widget):
		self.hide()		
########################################################################

def create_temp_file():
	return tempfile.mkstemp(prefix = 'tmp_filemanager_pdf_tools_')[1]

def dialog_save_as(title, original_file):
	# dialog.run()
	# if response == Gtk.ResponseType.OK:
	dialog = Gtk.FileChooserDialog(title,
									None,
								   Gtk.FileChooserAction.SAVE,
								   (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
									Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
	dialog.set_default_response(Gtk.ResponseType.OK)
	dialog.set_current_folder(os.path.dirname(original_file))
	dialog.set_filename(original_file)
	filter = Gtk.FileFilter()
	filter.set_name(_('Pdf files'))
	filter.add_mime_type('application/pdf')
	filter.add_pattern('*.pdf')
	dialog.add_filter(filter)
	if dialog.run() == Gtk.ResponseType.OK:
		filename = dialog.get_filename()
		if not filename.endswith('.pdf'):
			filename += '.pdf'
	else:
		filename = None
	dialog.destroy()
	return filename

def dialog_save_as_text(title, original_file):
	dialog = Gtk.FileChooserDialog(title,
									None,
								   Gtk.FileChooserAction.SAVE,
								   (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
									Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
	dialog.set_default_response(Gtk.ResponseType.OK)
	dialog.set_current_folder(os.path.dirname(original_file))
	dialog.set_filename(original_file)
	filter = Gtk.FileFilter()
	filter.set_name(_('Text file'))
	filter.add_mime_type('text/plain')
	filter.add_pattern('*.txt')
	dialog.add_filter(filter)
	if dialog.run() == Gtk.ResponseType.OK:
		filename = dialog.get_filename()
		if not filename.endswith('.txt'):
			filename += '.txt'
	else:
		filename = None
	dialog.destroy()
	return filename

		
########################################################################

def split_pdf(file_in):
	document = Poppler.Document.new_from_file('file://' + file_in, None)
	number_of_pages = document.get_n_pages()
	if number_of_pages>1:
		file_out,ext = os.path.splitext(file_in)		
		for i in range(0,number_of_pages):
			file_out_i = '%s_%s%s'%(file_out,i+1,ext)
			pdfsurface = cairo.PDFSurface(file_out_i,200,200)
			context = cairo.Context(pdfsurface)
			current_page = document.get_page(i)
			context.save()
			pdf_width,pdf_height = current_page.get_size()
			pdfsurface.set_size(pdf_width,pdf_height)
			current_page.render(context)
			context.restore()				
			context.show_page()		
			pdfsurface.flush()
			pdfsurface.finish()

def resize(file_in,file_out,width=1189,height=1682):
	document = Poppler.Document.new_from_file('file://' + file_in, None)
	number_of_pages = document.get_n_pages()
	width = float(width)
	height = float(height)
	horizontal = (width > height)
	pdfsurface = cairo.PDFSurface(file_out,width,height)
	context = cairo.Context(pdfsurface)
	for i in range(0,number_of_pages):
		current_page = document.get_page(i)
		widthi,heighti = current_page.get_size()
		horizontali = (widthi > heighti)
		if horizontal != horizontali:
			sw = width/heighti
			sh = height/widthi
			if sw<sh:
				scale = sw
			else:
				scale = sh
			context.save()
			mtr = cairo.Matrix()
			mtr.rotate(ROTATE_270/180.0*math.pi)
			context.transform(mtr)
			context.scale(scale,scale)
			context.translate(-widthi,0.0)			
			current_page.render(context)			
			context.restore()				
		else:
			sw = width/widthi
			sh = height/heighti
			if sw<sh:
				scale = sw
			else:
				scale = sh
			context.save()
			context.scale(scale,scale)
			current_page.render(context)			
			context.restore()
		context.show_page()			
	pdfsurface.flush()
	pdfsurface.finish()


def combine(file_in,file_out,filas=1,columnas=2,width=297,height=210,margen=0.0,byrows=True ):
	document = Poppler.Document.new_from_file('file://' + file_in, None)
	number_of_pages = document.get_n_pages()
	filas = float(filas)
	columnas = float(columnas)
	width = float(width)
	height = float(height)
	margen = float(margen)
	pdfsurface = cairo.PDFSurface(file_out,width,height)
	context = cairo.Context(pdfsurface)
	for i in range(0,number_of_pages,int(filas*columnas)):
		page = i-1
		for fila in range(0,int(filas)):
			for columna in range(0,int(columnas)):			
				page += 1		
				if byrows:
					aux_combine(page,document,fila,columna,width,height,filas,columnas,margen,context)
				else:
					aux_combine(page,document,columna,fila,width,height,filas,columnas,margen,context)
		context.show_page()
	pdfsurface.flush()
	pdfsurface.finish()

def aux_combine(page,document,fila,columna,width,height,filas,columnas,margen,context):		
	if page < document.get_n_pages():
		current_page = document.get_page(page)
		pdf_width,pdf_height = current_page.get_size()
		sw = (width-(filas+1.0)*margen)/pdf_width/columnas
		sh = (height-(columnas+1.0)*margen)/pdf_height/filas
		if sw<sh:
			scale = sw
		else:
			scale = sh
		x = float(columna) * width /columnas + (float(columna)+1.0)*margen
		y = (filas - float(fila) - 1.0) * height /float(filas) + (float(fila)+1.0)*margen
		context.save()		
		context.translate(x,y)
		context.scale(scale,scale)
		
		current_page.render(context)
		context.restore()		
	else:
		return 

def remove_ranges(file_in,file_out,ranges):
	pages =[]
	for rang in ranges:
		if len(rang)>1:
			for i in range(rang[0],rang[1]+1):
				if not i in pages:
					pages.append(i)
		else:
			if not rang[0] in pages:
				pages.append(rang[0])	
	document = Poppler.Document.new_from_file('file://' + file_in, None)
	number_of_pages = document.get_n_pages()
	temp_pdf = create_temp_file()
	pdfsurface = cairo.PDFSurface(temp_pdf,200,200)
	context = cairo.Context(pdfsurface)
	for i in range(0,number_of_pages):
		if i+1 not in pages:
			current_page = document.get_page(i)
			context.save()
			pdf_width,pdf_height = current_page.get_size()
			pdfsurface.set_size(pdf_width,pdf_height)
			current_page.render(context)
			context.restore()				
			context.show_page()		
	pdfsurface.flush()
	pdfsurface.finish()
	shutil.copy(temp_pdf, file_out)
	os.remove(temp_pdf)
	
def rotate_ranges_in_pdf(file_in,file_out,degrees,ranges,flip_horizontal=False,flip_vertical=False):
	pages =[]
	for rang in ranges:
		if len(rang)>1:
			for i in range(rang[0],rang[1]+1):
				if not i in pages:
					pages.append(i)
		else:
			if not rang[0] in pages:
				pages.append(rang[0])
	document = Poppler.Document.new_from_file('file://' + file_in, None)
	if document.get_n_pages() > 0:
		temp_pdf = create_temp_file()
		pdfsurface = cairo.PDFSurface(temp_pdf,200,200)
		context = cairo.Context(pdfsurface)
		for i in range(0,document.get_n_pages()):
			current_page = document.get_page(i)
			if i+1 in pages:
				if degrees == ROTATE_000 or degrees == ROTATE_180:
					pdf_width,pdf_height = current_page.get_size()
				else:
					pdf_height,pdf_width = current_page.get_size()
				pdfsurface.set_size(pdf_width,pdf_height)
				context.save()
				mtr = cairo.Matrix()
				mtr.rotate(degrees/180.0*math.pi)
				context.transform(mtr)			
				if degrees == ROTATE_090:
						context.translate(0.0,-pdf_width)
						print(degrees)
				elif degrees == ROTATE_180:
						context.translate(-pdf_width,-pdf_height)
				elif degrees == ROTATE_270:
						context.translate(-pdf_height,0.0)			
				if flip_vertical:
					context.scale(1,-1)
					if degrees == ROTATE_000 or degrees == ROTATE_180:
						context.translate(0,-pdf_height)
					else:
						context.translate(0,-pdf_width)
				if flip_horizontal:
					context.scale(-1,1)
					if degrees == ROTATE_000 or degrees == ROTATE_180:
						context.translate(-pdf_width,0)
					else:
						context.translate(-pdf_height,0)
				current_page.render(context)			
				context.restore()
			else:
				context.save()
				pdf_width,pdf_height = current_page.get_size()
				pdfsurface.set_size(pdf_width,pdf_height)
				current_page.render(context)
				context.restore()				
			context.show_page()		
		pdfsurface.flush()
		pdfsurface.finish()
		shutil.copy(temp_pdf, file_out)
		os.remove(temp_pdf)

def convert2png(file_in,file_out):
	im=Image.open(file_in)
	im.save(file_out)

def rotate_and_flip_pages(file_pdf_in,degrees=ROTATE_090,flip_vertical=False,flip_horizontal=False,overwrite=False):
	document = Poppler.Document.new_from_file('file://' + file_pdf_in, None)
	if document.get_n_pages() > 0:
		temp_pdf = create_temp_file()
		pdfsurface = cairo.PDFSurface(temp_pdf,200,200)
		context = cairo.Context(pdfsurface)
		for i in range(0,document.get_n_pages()):
			current_page = document.get_page(i)
			if degrees == ROTATE_000 or degrees == ROTATE_180:
				pdf_width,pdf_height = current_page.get_size()
			else:
				pdf_height,pdf_width = current_page.get_size()
			pdfsurface.set_size(pdf_width,pdf_height)
			context.save()
			mtr = cairo.Matrix()
			mtr.rotate(degrees/180.0*math.pi)
			context.transform(mtr)			
			if degrees == ROTATE_090:
					context.translate(0.0,-pdf_width)
					print(degrees)
			elif degrees == ROTATE_180:
					context.translate(-pdf_width,-pdf_height)
			elif degrees == ROTATE_270:
					context.translate(-pdf_height,0.0)			
			if flip_vertical:
				context.scale(1,-1)
				if degrees == ROTATE_000 or degrees == ROTATE_180:
					context.translate(0,-pdf_height)
				else:
					context.translate(0,-pdf_width)
			if flip_horizontal:
				context.scale(-1,1)
				if degrees == ROTATE_000 or degrees == ROTATE_180:
					context.translate(-pdf_width,0)
				else:
					context.translate(-pdf_height,0)
			current_page.render(context)			
			context.restore()
			context.show_page()		
		pdfsurface.flush()
		pdfsurface.finish()
		if overwrite:
			shutil.copy(temp_pdf, file_pdf_in)
		else:			
			shutil.copy(temp_pdf, get_output_filename(file_pdf_in,'rotated_'+str(int(degrees))))
		os.remove(temp_pdf)

def add_paginate_all_pages(file_pdf_in,color,font,size,horizontal_position,vertical_position,overwrite=False):
	document = Poppler.Document.new_from_file('file://' + file_pdf_in, None)
	number_of_pages = document.get_n_pages()
	if document.get_n_pages() > 0:
		temp_pdf = create_temp_file()
		pdfsurface = cairo.PDFSurface(temp_pdf,200,200)
		context = cairo.Context(pdfsurface)
		for i in range(0,number_of_pages):
			current_page = document.get_page(i)
			text = '%s/%s'%(i+1,number_of_pages)
			pdf_width,pdf_height = current_page.get_size()
			pdfsurface.set_size(pdf_width,pdf_height)
			context.save()
			current_page.render(context)
			context.restore()			
			context.save()
			context.set_source_rgba(*color)
			context.select_font_face(font)
			context.set_font_size(size)
			xbearing, ybearing, font_width, font_height, xadvance, yadvance = context.text_extents(text)
			if vertical_position == TOP:
				y = font_height
			elif vertical_position == MIDLE:
				y = (pdf_height + font_height)/2					
			elif vertical_position == BOTTOM:
				y = pdf_height
			if horizontal_position == LEFT:
				x = 0
			elif horizontal_position == CENTER:
				x = (pdf_width - font_width)/2
			elif horizontal_position == RIGHT:
				x = pdf_width - font_width	+ xbearing
			context.move_to(x,y)
			context.translate(x,y)
			context.show_text(text)
			context.restore()
			context.show_page()		
		pdfsurface.flush()
		pdfsurface.finish()
		if overwrite:
			shutil.copy(temp_pdf, file_pdf_in)
		else:			
			shutil.copy(temp_pdf, get_output_filename(file_pdf_in,'paginated'))
		os.remove(temp_pdf)

def add_textmark_to_all_pages(file_pdf_in,text,color,font,size,horizontal_position,vertical_position,overwrite=False):
	document = Poppler.Document.new_from_file('file://' + file_pdf_in, None)
	if document.get_n_pages() > 0:
		temp_pdf = create_temp_file()
		pdfsurface = cairo.PDFSurface(temp_pdf,200,200)
		context = cairo.Context(pdfsurface)
		for i in range(0,document.get_n_pages()):
			current_page = document.get_page(i)
			pdf_width,pdf_height = current_page.get_size()
			pdfsurface.set_size(pdf_width,pdf_height)
			context.save()
			current_page.render(context)
			context.restore()			
			context.save()
			context.set_source_rgba(*color)
			context.select_font_face(font)
			context.set_font_size(size)
			xbearing, ybearing, font_width, font_height, xadvance, yadvance = context.text_extents(text)
			if vertical_position == TOP:
				y = font_height
			elif vertical_position == MIDLE:
				y = (pdf_height + font_height)/2					
			elif vertical_position == BOTTOM:
				y = pdf_height
			if horizontal_position == LEFT:
				x = 0
			elif horizontal_position == CENTER:
				x = (pdf_width - font_width)/2
			elif horizontal_position == RIGHT:
				x = pdf_width - font_width	+ xbearing
			context.move_to(x,y)
			context.translate(x,y)
			context.show_text(text)
			context.restore()
			context.show_page()		
		pdfsurface.flush()
		pdfsurface.finish()
		if overwrite:
			shutil.copy(temp_pdf, file_pdf_in)
		else:			
			shutil.copy(temp_pdf, get_output_filename(file_pdf_in,'textmarked'))
		os.remove(temp_pdf)

def add_watermark_to_all_pages(file_pdf_in,file_image_in,horizontal_position,vertical_position,overwrite=False):
	document = Poppler.Document.new_from_file('file://' + file_pdf_in, None)
	if document.get_n_pages() > 0:
		temp_pdf = create_temp_file()
		watermark_surface = cairo.ImageSurface.create_from_png(file_image_in)
		watermark_width = watermark_surface.get_width()
		watermark_height = watermark_surface.get_height()	
		pdfsurface = cairo.PDFSurface(temp_pdf,200,200)
		context = cairo.Context(pdfsurface)
		for i in range(0,document.get_n_pages()):
			current_page = document.get_page(i)
			pdf_width,pdf_height = current_page.get_size()
			pdfsurface.set_size(pdf_width,pdf_height)
			context.save()
			current_page.render(context)
			context.restore()
			context.save()
			if vertical_position == TOP:
				y = 0
			elif vertical_position == MIDLE:
				y = (pdf_height - watermark_height/MMTOPIXEL)/2					
			elif vertical_position == BOTTOM:
				y = pdf_height - watermark_height/MMTOPIXEL
			if horizontal_position == LEFT:
				x = 0
			elif horizontal_position == CENTER:
				x = (pdf_width - watermark_width/MMTOPIXEL)/2
			elif horizontal_position == RIGHT:
				x = pdf_width - watermark_width/MMTOPIXEL	
			context.translate(x,y)
			context.scale(1.0/MMTOPIXEL,1.0/MMTOPIXEL)
			context.set_source_surface(watermark_surface)
			context.paint()
			context.restore()
			context.show_page()		
		pdfsurface.flush()
		pdfsurface.finish()
		if overwrite:
			shutil.copy(temp_pdf, file_pdf_in)
		else:			
			shutil.copy(temp_pdf, get_output_filename(file_pdf_in,'watermarked'))
		os.remove(temp_pdf)

def extract_ranges(file_in,file_out,ranges):
	pages =[]
	for rang in ranges:
		if len(rang)>1:
			for i in range(rang[0],rang[1]+1):
				if not i in pages:
					pages.append(i)
		else:
			if not rang[0] in pages:
				pages.append(rang[0])	
	document = Poppler.Document.new_from_file('file://' + file_in, None)
	number_of_pages = document.get_n_pages()
	temp_pdf = create_temp_file()
	pdfsurface = cairo.PDFSurface(temp_pdf,200,200)
	context = cairo.Context(pdfsurface)
	for i in range(0,number_of_pages):
		if i+1 in pages:
			current_page = document.get_page(i)
			context.save()
			pdf_width,pdf_height = current_page.get_size()
			pdfsurface.set_size(pdf_width,pdf_height)
			current_page.render(context)
			context.restore()				
			context.show_page()		
	pdfsurface.flush()
	pdfsurface.finish()
	shutil.copy(temp_pdf, file_out)
	os.remove(temp_pdf)


def rotate_some_pages_in_pdf(file_in,file_out,degrees,first_page,last_page):
	document = Poppler.Document.new_from_file('file://' + file_in, None)
	if document.get_n_pages() > 0:
		temp_pdf = create_temp_file()
		pdfsurface = cairo.PDFSurface(temp_pdf,200,200)
		context = cairo.Context(pdfsurface)
		for i in range(0,document.get_n_pages()):
			current_page = document.get_page(i)
			if i>=first_page and i<=last_page:
				if degrees == ROTATE_000 or degrees == ROTATE_180:
					pdf_width,pdf_height = current_page.get_size()
				else:
					pdf_height,pdf_width = current_page.get_size()
				pdfsurface.set_size(pdf_width,pdf_height)
				context.save()
				mtr = cairo.Matrix()
				mtr.rotate(degrees/180.0*math.pi)
				context.transform(mtr)			
				if degrees == ROTATE_090:
						context.translate(0.0,-pdf_width)
						print(degrees)
				elif degrees == ROTATE_180:
						context.translate(-pdf_width,-pdf_height)
				elif degrees == ROTATE_270:
						context.translate(-pdf_height,0.0)			
				if flip_vertical:
					context.scale(1,-1)
					if degrees == ROTATE_000 or degrees == ROTATE_180:
						context.translate(0,-pdf_height)
					else:
						context.translate(0,-pdf_width)
				if flip_horizontal:
					context.scale(-1,1)
					if degrees == ROTATE_000 or degrees == ROTATE_180:
						context.translate(-pdf_width,0)
					else:
						context.translate(-pdf_height,0)
				current_page.render(context)			
				context.restore()
			else:
				context.save()
				pdf_width,pdf_height = current_page.get_size()
				pdfsurface.set_size(pdf_width,pdf_height)
				current_page.render(context)
				context.restore()				
			context.show_page()		
		pdfsurface.flush()
		pdfsurface.finish()
		shutil.copy(temp_pdf, file_out)
		os.remove(temp_pdf)

def extract_pages(file_in,file_out,first_page,last_page):
	document = Poppler.Document.new_from_file('file://' + file_in, None)
	number_of_pages = document.get_n_pages()
	if first_page > number_of_pages-1:
		first_page = number_of_pages-1
	if last_page < first_page:
		last_page = first_page
	if last_page > number_of_pages-1:
		last_page = number_of_pages-1
	temp_pdf = create_temp_file()
	pdfsurface = cairo.PDFSurface(temp_pdf,200,200)
	context = cairo.Context(pdfsurface)
	for i in range(first_page,last_page+1):
		current_page = document.get_page(i)
		context.save()
		pdf_width,pdf_height = current_page.get_size()
		pdfsurface.set_size(pdf_width,pdf_height)
		current_page.render(context)
		context.restore()				
		context.show_page()		
	pdfsurface.flush()
	pdfsurface.finish()
	shutil.copy(temp_pdf, file_out)
	os.remove(temp_pdf)

def remove_pages(file_in,file_out,first_page,last_page):
	document = Poppler.Document.new_from_file('file://' + file_in, None)
	number_of_pages = document.get_n_pages()
	if first_page > number_of_pages-1:
		first_page = number_of_pages-1
	if last_page < first_page:
		last_page = first_page
	if last_page > number_of_pages-1:
		last_page = number_of_pages-1
	temp_pdf = create_temp_file()
	pdfsurface = cairo.PDFSurface(temp_pdf,200,200)
	context = cairo.Context(pdfsurface)
	for i in range(0,number_of_pages):
		if i not in list(range(first_page,last_page+1)):
			current_page = document.get_page(i)
			context.save()
			pdf_width,pdf_height = current_page.get_size()
			pdfsurface.set_size(pdf_width,pdf_height)
			current_page.render(context)
			context.restore()				
			context.show_page()		
	pdfsurface.flush()
	pdfsurface.finish()
	shutil.copy(temp_pdf, file_out)
	os.remove(temp_pdf)


def join_files(files,file_out):
	temp_pdf = create_temp_file()
	pdfsurface = cairo.PDFSurface(temp_pdf,200,200)
	context = cairo.Context(pdfsurface)
	for file_in in files:
		document = Poppler.Document.new_from_file('file://' + file_in, None)
		number_of_pages = document.get_n_pages()		
		for i in range(0,number_of_pages):
			current_page = document.get_page(i)
			context.save()
			pdf_width,pdf_height = current_page.get_size()
			pdfsurface.set_size(pdf_width,pdf_height)
			current_page.render(context)
			context.restore()				
			context.show_page()		
	pdfsurface.flush()
	pdfsurface.finish()
	shutil.copy(temp_pdf, file_out)
	os.remove(temp_pdf)
	
def get_output_filename(file_in,modificator):
	if os.path.exists(file_in) and os.path.isfile(file_in):
		head, tail = os.path.split(file_in)
		root, ext = os.path.splitext(tail)
		file_out = os.path.join(head,root+'_'+modificator+ext)
		return file_out
	return None

def get_files(files_in):
	files = []
	for file_in in files_in:
		print(file_in)
		file_in = file_in.get_uri()[7:]
		if os.path.isfile(file_in):
			files.append(file_in)
	if len(files)>0:
		return files
	return None

def get_num(chain):
	try:
		chain = chain.strip() # removing spaces
		return int(float(chain))
	except:
		return None

def get_ranges(chain):
	ranges = []
	if chain.find(',') > -1:
		for part in chain.split(','):
			if part.find('-') > -1:
				parts = part.split('-')
				if len(parts) > 1:
					f = get_num(parts[0])
					t = get_num(parts[1])
					if f != None and t !=None:
						ranges.append([f,t])
			else:
				el = get_num(part)
				if el:
					ranges.append([el])
	elif chain.find('-') > -1:
		parts = chain.split('-')
		if len(parts) > 1:
			f = get_num(parts[0])
			t = get_num(parts[1])
			if f != None and t !=None:
				ranges.append([f,t])
	else:
		el = get_num(chain)
		if el:
			ranges.append([el])
	return ranges

"""
Tools to manipulate pdf
"""	
class PdfToolsMenuProvider(GObject.GObject, FileManager.MenuProvider):
	"""Implements the 'Replace in Filenames' extension to the File Manager right-click menu"""

	def __init__(self):
		"""File Manager crashes if a plugin doesn't implement the __init__ method"""
		pass

	def all_files_are_pdf(self,items):
		for item in items:
			fileName, fileExtension = os.path.splitext(item.get_uri()[7:])
			if fileExtension != '.pdf':
				return False
		return True

	def all_files_are_images(self,items):
		for item in items:
			fileName, fileExtension = os.path.splitext(item.get_uri()[7:])
			if fileExtension.lower() in EXTENSIONS:
				return True
		return False

	def resize_pdf_pages(self,menu,selected):
		files = get_files(selected)
		if files:
			file_in = files[0]
			cd = ResizeDialog(_('Resize pages'))
			if cd.run() == Gtk.ResponseType.ACCEPT:
				size = cd.get_size()
				if cd.is_vertical():
					width = size[0]
					height = size[1]
				else:
					width = size[1]
					height = size[0]
				cd.destroy()
				file_out = dialog_save_as(_('Select file to save new file'), file_in)
				if file_out:
					resize(file_in,file_out,width,height)
			cd.destroy()

	def combine_pdf_pages(self,menu,selected):
		files = get_files(selected)
		if files:
			file_in = files[0]
			cd = CombineDialog(_('Combine pages'))
			if cd.run() == Gtk.ResponseType.ACCEPT:
				size = cd.get_size()
				if cd.is_vertical():
					width = size[0]
					height = size[1]
				else:
					width = size[1]
					height = size[0]
				filas = cd.get_rows()
				columnas = cd.get_columns()
				byrows = cd.is_sort_by_rows()
				margen = cd.get_margin()
				cd.destroy()
				file_out = dialog_save_as(_('Select file to save new file'), file_in)
				if file_out:
					combine(file_in,file_out,filas,columnas,width,height,margen,byrows )
			cd.destroy()
			
	def join_pdf_files(self,menu,selected):
		files = get_files(selected)
		if files:
			jpd = JoinPdfsDialog(_('Join pdf files'),files)
			if jpd.run() == Gtk.ResponseType.ACCEPT:
				files = jpd.get_pdf_files()
				jpd.destroy()
				if len(files)>0:
					file0 = os.path.join(os.path.dirname(files[0]),'joined_files.pdf')
					file_out = dialog_save_as(_('Select file to save new file'), file0)
					if file_out:
						join_files(files,file_out)
			jpd.destroy()

	def paginate(self,*args):
		menu_item, sel_items = args
		files = get_files(sel_items)
		if len(files)>0:
			file0 = files[0]
			wd = PaginateDialog(file0)
			if wd.run() == Gtk.ResponseType.ACCEPT:
				wd.hide()
				color =wd.get_color()
				font = wd.get_font()
				size =wd.get_size()
				hoption = wd.get_horizontal_option()
				voption = wd.get_vertical_option()
				for afile in files:
					add_paginate_all_pages(afile,color,font,size,hoption,voption,wd.rbutton0.get_active())
			wd.destroy()

	def textmark(self,*args):
		menu_item, sel_items = args
		files = get_files(sel_items)
		if len(files)>0:
			file0 = files[0]
			wd = TextmarkDialog(file0)
			if wd.run() == Gtk.ResponseType.ACCEPT:
				wd.hide()
				text = text.get_text()
				color =wd.get_color()
				font = wd.get_font()
				size =wd.get_size()
				hoption = wd.get_horizontal_option()
				voption = wd.get_vertical_option()
				for afile in files:
					add_textmark_to_all_pages(afile,text,color,font,size,hoption,voption,wd.rbutton0.get_active())
			wd.destroy()

	def watermark(self,*args):
		menu_item, sel_items = args
		files = get_files(sel_items)
		if len(files)>0:
			file0 = files[0]
			wd = WatermarkDialog(file0)
			if wd.run() == Gtk.ResponseType.ACCEPT:
				wd.hide()
				hoption = wd.get_horizontal_option()
				voption = wd.get_vertical_option()
				for afile in files:
					print('------------------------------------------------')
					print(afile)
					add_watermark_to_all_pages(afile,wd.get_image_filename(),hoption,voption,wd.rbutton0.get_active())
					print('------------------------------------------------')
			wd.destroy()

	def rotate_or_flip(self,*args):
		menu_item, sel_items = args
		files = get_files(sel_items)
		if len(files)>0:
			file0 = files[0]
			fd = FlipDialog(_('Rotate files'),file0)
			degrees = 0
			if fd.run() == Gtk.ResponseType.ACCEPT:
				fd.hide()
				for afile in files:
					if fd.rbutton2.get_active():
						rotate_and_flip_pages(afile,ROTATE_090, fd.switch1.get_active(),fd.switch2.get_active(),fd.rbutton1.get_active())
					elif fd.rbutton3.get_active():
						rotate_and_flip_pages(afile,ROTATE_180, fd.switch1.get_active(),fd.switch2.get_active(),fd.rbutton1.get_active())
					elif fd.rbutton4.get_active():
						rotate_and_flip_pages(afile,ROTATE_270, fd.switch1.get_active(),fd.switch2.get_active(),fd.rbutton1.get_active())
			fd.destroy()
			
	def rotate_some_pages(self,menu,selected):
		files = get_files(selected)
		if files:
			file0 = files[0]
			document = Poppler.Document.new_from_file('file://' + file0, None)
			last_page = document.get_n_pages()
			spd = SelectPagesRotateDialog(_('Rotate some pages'),last_page)
			if spd.run() == Gtk.ResponseType.ACCEPT:			
				ranges = get_ranges(spd.entry1.get_text())				
				if spd.rbutton1.get_active():
					degrees = 270
				elif spd.rbutton2.get_active():
					degrees = 90
				else:
					degrees = 180
				spd.destroy()
				if len(ranges)>0:
					file_out = dialog_save_as(_('Select file to save new file'), file0)
					if file_out:
						rotate_ranges_in_pdf(file0,file_out,degrees,ranges)
			else:
				spd.destroy()
				
	def about(self,menu,selected):
		ad=Gtk.AboutDialog()
		ad.set_name(APP)
		ad.set_icon_name(ICON)
		ad.set_version(VERSION)
		ad.set_copyright('Copyrignt (c) 2012-2013\nLorenzo Carbonell')
		ad.set_comments(_('Tools to manage pdf files'))
		ad.set_license(''+
		'This program is free software: you can redistribute it and/or modify it\n'+
		'under the terms of the GNU General Public License as published by the\n'+
		'Free Software Foundation, either version 3 of the License, or (at your option)\n'+
		'any later version.\n\n'+
		'This program is distributed in the hope that it will be useful, but\n'+
		'WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY\n'+
		'or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for\n'+
		'more details.\n\n'+
		'You should have received a copy of the GNU General Public License along with\n'+
		'this program.  If not, see <http://www.gnu.org/licenses/>.')
		ad.set_website('http://www.atareao.es')
		ad.set_website_label('http://www.atareao.es')
		ad.set_authors(['Lorenzo Carbonell <lorenzo.carbonell.cerezo@gmail.com>'])
		ad.set_documenters(['Lorenzo Carbonell <lorenzo.carbonell.cerezo@gmail.com>'])
		ad.set_program_name(APP)
		ad.set_logo_icon_name(ICON)
		ad.run()
		ad.destroy()		
		
	def remove_some_pages(self,menu,selected):
		files = get_files(selected)
		if files:
			file0 = files[0]
			document = Poppler.Document.new_from_file('file://' + file0, None)
			last_page = document.get_n_pages()
			spd = SelectPagesDialog(_('Remove some pages'),last_page)
			if spd.run() == Gtk.ResponseType.ACCEPT:
				ranges = get_ranges(spd.entry1.get_text())
				spd.destroy()
				if len(ranges)>0:
					file_out = dialog_save_as(_('Select file to save new file'), file0)
					if file_out:
						remove_ranges(file0,file_out,ranges)
			else:
				spd.destroy()

	def split_pdf_files(self,menu,selected):
		files = get_files(selected)
		if files:
			file0 = files[0]
			split_pdf(file0)
		
	def extract_some_pages(self,menu,selected):
		files = get_files(selected)
		if files:
			file0 = files[0]
			document = Poppler.Document.new_from_file('file://' + file0, None)
			last_page = document.get_n_pages()
			spd = SelectPagesDialog(_('Extract some pages'),last_page)
			if spd.run() == Gtk.ResponseType.ACCEPT:
				ranges = get_ranges(spd.entry1.get_text())
				spd.destroy()
				if len(ranges)>0:				
					file_out = dialog_save_as(_('Select file to save extracted pages'), file0)
					if file_out:
						extract_ranges(file0,file_out,ranges)
			else:
				spd.destroy()
				
	def extract_text(self,menu,selected):
		files = get_files(selected)
		if files:
			file0 = files[0]
			file_out = dialog_save_as_text(_('Select file to save extracted text'), file0)
			if file_out:
				extract_text(file0,file_out)
		
	def get_file_items(self, window, sel_items):
		"""Adds the 'Replace in Filenames' menu item to the File Manager right-click menu,
		   connects its 'activate' signal to the 'run' method passing the selected Directory/File"""
		if self.all_files_are_pdf(sel_items):
			top_menuitem = FileManager.MenuItem(name='PdfToolsMenuProvider::Gtk-pdf-tools',
									 label=_('Pdf Tools'),
									 tip=_('Tools to manipulate pdf files'),
									 icon='Gtk-find-and-replace')
			#
			submenu = FileManager.Menu()
			top_menuitem.set_submenu(submenu)
			sub_menus = []
			items = [
			('01',_('Rotate and flip'),_('rotate_and_flip pdf files'),self.rotate_or_flip),
			('02',_('Watermark'),_('Watermark pdffiles'),self.watermark),
			('03',_('Textmark'),_('Textmark pdf files'),self.textmark),
			('04',_('Paginate'),_('Paginate pdf files'),self.paginate),
			('05',_('Rotate pages'),_('Rotate pages of the document files'),self.rotate_some_pages),
			('06',_('Remove pages'),_('Remove pages of the document files'),self.remove_some_pages),
			('07',_('Extract pages'),_('Extract pages of the document files'),self.extract_some_pages),
			('08',_('Join pdf files'),_('Join pdf files in one document'),self.join_pdf_files),
			('09',_('Split pdf files'),_('Split a pdf in several documents'),self.split_pdf_files),
			('10',_('Combine pdf pages'),_('Combine pdf pages in one page'),self.combine_pdf_pages),
			('11',_('Resize pdf pages'),_('Resize pdf pages'),self.resize_pdf_pages),
			]
			for item in items:
				sub_menuitem = FileManager.MenuItem(name='PdfToolsMenuProvider::Gtk-pdf-tools-'+item[0],
								 label=item[1],tip=item[2])
				sub_menuitem.connect('activate', item[3], sel_items)
				submenu.append_item(sub_menuitem)		
			#		
			sub_menuitem_98 = FileManager.MenuItem(name='PdfToolsMenuProvider::Gtk-None',
									 label=SEPARATOR)
			submenu.append_item(sub_menuitem_98)
			#		
			sub_menuitem_99 = FileManager.MenuItem(name='PdfToolsMenuProvider::Gtk-pdf-tools-99',
									 label=_('About'),
									 tip=_('About'),
									 icon='Gtk-find-and-replace')
			sub_menuitem_99.connect('activate', self.about, sel_items)
			submenu.append_item(sub_menuitem_99)
			#		
			return top_menuitem,
		elif self.all_files_are_images(sel_items):
			pass
		return

if __name__ == '__main__':
	cd = CombineDialog('Test')
	cd.run()
