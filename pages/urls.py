''' 
URL to View Regular Expression mappings 

@author Evan Kleist
@author Russell Mezzetta
@author Mark Gius
'''
from django.conf.urls.defaults import *
from django.views.generic.simple import direct_to_template

urlpatterns = patterns('',
	(r'^submitQuiz/', 'pages.quiz.views.submitQuiz'),
	(r'^newLesson/', 'pages.lesson.views.create_lesson'),
	(r'^newQuiz/', 'pages.quiz.views.create_quiz'),
	(r'^edit/', 'pages.views.edit_page'),
	(r'^move/', 'pages.views.move_page'),
	(r'^preview/', 'pages.views.show_page_preview'),	
	(r'', 'pages.views.show_page'),
)
