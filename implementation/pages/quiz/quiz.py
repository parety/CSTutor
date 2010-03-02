'''
quiz.py fil for quiz related operations.

Contains operations for all lessons

@author Evan Kleist
'''
from django.template.defaultfilters import slugify
from models import *
from question.models import *
from question.question import isMultipleChoiceQuestion
from question.question import removeQuestion
from pages.page import removePage
from stats.models import Stat


def addMultipleChoiceQuestion(self):
	'''
		Takes a quiz and adds a blank multiple choice question to it
	'''
	questions = self.questions.all()
	newQuestion = MultipleChoiceQuestion(order=(len(questions)+1), quiz=self)
	newQuestion.save()
	return newQuestion

def addCodeQuestion(self):
	'''
		Takes a quiz and adds a blank code question to it
	'''
	questions = self.questions.all()
	newQuestion = CodeQuestion(order=(len(questions)+1), quiz=self)
	newQuestion.save()
	return newQuestion

def publishQuiz(self):
	'''
		Takes a working copy of a quiz and copies it over to the published version of the quiz
	'''
	publishedSlug = safeSlug(self.slug)
	publishedQuiz = Quiz.objects.get(slug=publishedSlug)

	# Copy Title
	publishedQuiz.text = self.text

	# Copy Hidden
	publishedQuiz.hidden = self.hidden

	# Copy Prerequisites
	curPrereqs = publishedQuiz.prerequisites.all()
	for p in curPrereqs:
		p.delete()
	curPrereqs = self.prerequisites.all()
	for p in curPrereqs:
		newPrereq = Prerequisite(containingQuiz = publishedQuiz, requiredQuiz = p.requiredQuiz)
		newPrereq.save()

	# Copy Questions
	curQuestions = publishedQuiz.questions.all()
	for q in curQuestions:
		removeQuestion(q)
	curQuestions = self.questions.all()
	for q in curQuestions:
		if (isMultipleChoiceQuestion(q)):
			q = q.multiplechoicequestion
			newQ = MultipleChoiceQuestion(text = q.text, order = q.order, quiz = publishedQuiz)
			newQ.save()
			# Copy Answers
			curAnswers = q.answers.all()
			for a in curAnswers:
				newA = Answer(question = newQ, correct = a.correct, order = a.order, text = a.text)
				newA.save()
		else:
			q = q.codequestion
			newQ = CodeQuestion(text = q.text, order = q.order, quiz = publishedQuiz, beforeCode = q.beforeCode, showBeforeCode = q.showBeforeCode, editableCode = q.editableCode, afterCode = q.afterCode, showAfterCode = q.showAfterCode, expectedOutput = q.expectedOutput)
			newQ.save()
			

def removeQuiz(self):
	'''
		Removes a quiz from the database, as well as all related 
		objects
	'''
	questions = self.questions.all()
	prerequisites = self.prerequisites.all()
	workingQuiz = Quiz.objects.get(slug=(self.slug + "_workingCopy"))
	workingQuestions = workingQuiz.questions.all()
	workingPrerequisites = workingQuiz.prerequisites.all()

	# Remove Questions
	for q in questions:
		removeQuestion(q)
	for q in workingQuestions:
		removeQuestion(q)

	# Remove Prerequisites
	for p in prerequisites:
		p.delete()
	for p in workingPrerequisites:
		p.delete()

	# Remove Pages
	removePage(self)
	removePage(workingQuiz)
	# should also remove all associated quiz objects such as stats, questions, answers, paths
	return 0

def reorderQuestions(self):
	'''
		Takes a quiz, retrieves its questions, and then reorders the 
		questions into a valid state.
	'''
	questions = self.questions.all().order_by("order")
	qNum = 1
	for q in questions:
		q.order = qNum
		q.save()
		qNum = qNum + 1
	# Sanity check to make sure the question ordering is still valid
	if (validateQuestionOrder(self)):
		return 0
	return -1

def safeSlug(page_slug):
	'''
		Takes a quiz slug and makes sure they are not trying to directly access
		the working copy. If so, it returns the slug to the published copy
	'''

	if (page_slug.endswith("_workingCopy") != False and page_slug.find("_workingCopy") == len(page_slug) - 12):
		return page_slug[:-12]

	return page_slug
		

def saveQuiz(request, course, pid):
	'''
		Takes a request, a course, and a page id. It then pulls the 
		quiz from the post data and updates the elements in the 
		database. Before saving, it validates for proper data
	'''
	data = {}
	errors = []
	quiz = Page.objects.get(slug=(pid + "_workingCopy")).quiz
	publishedQuiz = Page.objects.get(slug=pid).quiz

	if (request.method != "POST"):
		errors.append("Trying to save quiz from a non POST request")

	elif "Save" in request.POST or "Publish" in request.POST:
		errors = validateQuizFromPost(quiz, request)
		if (len(errors) == 0):
			quiz.text = request.POST["quizTitle"]
			quiz.name = request.POST["quizTitle"]
			publishedQuiz.slug = slugify(quiz.name)
			quiz.slug = publishedQuiz.slug + "_workingCopy"
			if "hidden" in request.POST:
				quiz.hidden = True
			else:
				quiz.hidden = False
			# Delete current prerequisites
			for p in quiz.prerequisites.all():
				p.delete()
			if "prereqs" in request.POST:
				# Create prerequisites
				for p in request.POST.getlist("prereqs"):
					reqQuiz = Course.objects.get(slug=course).pages.get(slug=p).quiz
					newPrereq = Prerequisite(containingQuiz=quiz, requiredQuiz=reqQuiz)
					newPrereq.save()
				
			questions = quiz.questions.all()
			for q in questions:
				if (isMultipleChoiceQuestion(q)):
					q = q.multiplechoicequestion
					for a in q.answers.all():
						a.text = request.POST['mcq%sa%s' % (q.order, a.order)]
						a.correct = (request.POST['mcq%sac' % q.order] == str(a.order))
						a.save()
					q.text = request.POST['mcq%stext' % q.order]
					q.order = request.POST['mcq%sorder' % q.order]
				else:
					q = q.codequestion
					q.text = request.POST['cq%stext' % q.order]
					q.expectedOutput = request.POST['cq%seo' % q.order]
					q.order = request.POST['cq%sorder' % q.order]
				q.save()

			quiz.save()
			publishedQuiz.save()

	data = {"quiz_slug":publishedQuiz.slug, "errors":errors}
	return data

def scoreQuiz(self, request, course_slug, quiz_slug):
	'''
		Takes a quiz and a request. Pulls the submitted answers from 
		the form contained in the request and compares it to the 
		correct answers specified in the quiz. Generates a statistic 
		for a quiz, adds it to the database and returns their score.
	'''
	questions = self.questions.all()
	course = Course.objects.get(slug=course_slug)
	score = 0

	for q in questions:
		if (isMultipleChoiceQuestion(q)):
			q = q.multiplechoicequestion
			theirAnswer = request.POST['mcq%s' % q.order]
			if (q.answers.get(order=theirAnswer).correct):
				score = score + 1
		else:
			q = q.codequestion
			print "Grade code question\n"

	if (not request.user.is_anonymous()):
		Stat.CreateStat(course, self, request.user, score)
	
	return score

def validateQuestionOrder(self):
	'''
		Takes in a quiz, and verifies that all of its questions have
		a unique ordering, and are ordered from 1 -> # of questions

		Returns True if the above constraints are met, False otherwise
	'''
	questions = self.questions.all()
	usedNumbers = set([question.order for question in questions])
	if (len(questions) == 0):
		return True
	if len(questions) != len(usedNumbers) or \
		min(usedNumbers) != 1 or max(usedNumbers) != len(questions):
			return False
	return True

def validateQuizFromPost(self, request):
	'''
		Takes a request containing POST data for a quiz and makes sure
		any changed elements are valid. It returns and array array of
		or an emtpy array if no errors were found
	'''
	errors = []
	questions = self.questions.all();
	
	# Title - Make sure its not blank
	if (len(request.POST["quizTitle"]) == 0):
		errors.append("Quiz Title can not be blank")

	# Hidden - There can be no errors in this

	# Prerequisites - There can be no errors in this

	for q in questions:
		if (isMultipleChoiceQuestion(q)):
			# Multiple Choice Question - Make sure its not blank
			q = q.multiplechoicequestion
			if (len(request.POST["mcq%stext" % q.order]) == 0):
				errors.append("Question cannot have a blank prompt")

			answers = q.answers.all()
			
			# Question must have at least two possible answers
			if (len(answers) < 2):
				errors.append("Answer must have at least two possible answers")

			for a in answers:
				# Answer must not be blank
				if (len(request.POST["mcq%sa%s" % (q.order, a.order)]) == 0):
					errors.append("Answer must not be blank")

			# Question must have a correct answer
			if (not ("mcq%sac" % q.order) in request.POST):
				errors.append("Question must have a correct answer")
		else:
			q = q.codequestion
			
			# Prompt must not be blank
			if (len(request.POST["cq%stext" % q.order]) == 0):
				errors.append("Code Question prompt must not be blank")

			# Expected output must not be blank
			if (len(request.POST["cq%seo" % q.order]) == 0):
				errors.append("Code Question expected output must not be blank")

	# Question Ordering - Must be valid
	if (not validateQuestionOrder(self)):
		errors.append("Questions must have a valid ordering")

	return errors
	
