'''
quiz.py for quiz related operations.

Contains operations that act on a quiz

@author Evan Kleist
'''
from django.template.defaultfilters import slugify
from models import *
from question.models import *
from question.question import *
from pages.page import removePage
from stats.models import Stat
from codeshell.pythoncode import *
from stats.models import Stat
from stats.stat import getUserBestScore

def addCodeQuestion(self):
	'''
	Adds a new code question to a quiz

	Takes the quiz being operated on

	@author Evan Kleist
	'''
	questions = self.questions.all()
	newQuestion = CodeQuestion(order=(len(questions)+1), quiz=self)
	newQuestion.save()
	return newQuestion

def addMultipleChoiceQuestion(self):
	'''
	Adds a blank multiple choice question to a quiz, as well as 2 blank answers

	Takes the quiz being operated on
	@author Evan Kleist
	'''
	questions = self.questions.all()
	newQuestion = MultipleChoiceQuestion(order=(len(questions)+1), quiz=self)
	newQuestion.save()
	addAnswer(newQuestion)
	addAnswer(newQuestion)
	return newQuestion

def addPath(self, request, course_slug):
	'''
		Adds a new path to a quiz. Calling this method from anything
		other than the Add Path Form will cause an exception.

		Parameters:
		   self - the quiz being operated on
		   request - an HttpRequest that contains POST data representing the
		             new path to be added. This data is obtained by the form
		             displayed when the add path button is pressed.
		   course_slug - the course slug for the course that the quiz belongs to

		pre: must be a POST and contain the post data

		@author Evan Kleist
	'''
	errors = []
	try:
		lowScore = int(request.POST["LowScore"])
		if (lowScore < 0 or lowScore > 100):
			errors.append("Low Score must be between 0 and 100")

		try:
			matchingPath = matchPath(self, lowScore)
			errors.append("A path that matches this range exists already")
		except NoMatchingPath:
			pass			
	except ValueError:
		lowScore = 0
		errors.append("Low Score must be an integer")

	try:
		highScore = int(request.POST["HighScore"])
		if (highScore < 0 or highScore > 100):
			errors.append("High Score must be between 0 and 100")
		if (highScore < lowScore):
			errors.append("Low Score must be less than or equal to High Score")
	except ValueError:
		errors.append("High Score must be an integer")

	course = Course.objects.get(slug=course_slug)
	page = course.pages.get(slug=request.POST["pathPage"])
	passing = "passing" in request.POST
	dialogue = request.POST["dialogue"]

	if (len(errors) == 0):
		newPath = Path(quiz = self, highscore = highScore, lowscore = lowScore, toPage = page, passed = passing, text = dialogue)
		newPath.save()
		publishedCopy = Quiz.objects.get(slug = safeSlug(self.slug), course=course)
		publishedCopy.upToDate = False
		publishedCopy.save()

	return errors

def checkPrerequisites(self, user):
	'''
		Looks up the user's statistics up and makes sure all of the quizzes 
		prerequisites havee been met by the user. If the user has edit 
		permissions on the course,	then it returns true. This is because a
		editor should stil be able to view questions of the quiz they can edit.
		If prerequisites have not been met or the user is not an editor, it 
		returns false

		Parameters:
		   self - the quiz being operated on
		   user - the user being checked on
	
		@author Evan Kleist
	'''
	prereqs = self.prerequisites.all()
	if (len(prereqs) > 0):
		if (user.is_anonymous()):
			return False
		enrollment = user.enrollments.get(course=self.course)
		if (not enrollment.edit):
			for p in prereqs:
				requiredQuiz = p.requiredQuiz
				score = getUserBestScore(user, requiredQuiz)
				if (score == -1):
					return False
				path = matchPath(requiredQuiz, score)
				if (path.passed == False):
					return False

	return True

def copyQuiz(quiz1, quiz2):
	'''
		Copies the contents of quiz1 into quiz2

		Parameters:
		   quiz1 - the quiz being copied from
			quiz2 - the quiz being copied to

		@author Evan Kleist
	'''

	# Copy Title
	quiz2.text = quiz1.text
	quiz2.name = quiz1.name

	# Copy Hidden
	quiz2.hidden = quiz1.hidden

	# Copy Prerequisites
	curPrereqs = quiz2.prerequisites.all()
	for p in curPrereqs:
		p.delete()
	curPrereqs = quiz1.prerequisites.all()
	for p in curPrereqs:
		newPrereq = Prerequisite(containingQuiz = quiz2, requiredQuiz = p.requiredQuiz)
		newPrereq.save()

	# Copy Paths
	curPaths = quiz2.paths.all()
	for p in curPaths:
		p.delete()
	curPaths = quiz1.paths.all()
	for p in curPaths:
		newPath = Path(quiz = quiz2, lowscore = p.lowscore, highscore = p.highscore, text = p.text, passed = p.passed, toPage = p.toPage)
		newPath.save()

	# Copy Questions
	curQuestions = quiz2.questions.all()
	for q in curQuestions:
		removeQuestion(q)
	curQuestions = quiz1.questions.all()
	for q in curQuestions:
		if (isMultipleChoiceQuestion(q)):
			q = q.multiplechoicequestion
			newQ = MultipleChoiceQuestion(text = q.text, order = q.order, quiz = quiz2)
			newQ.save()
			# Copy Answers
			curAnswers = q.answers.all()
			for a in curAnswers:
				newA = Answer(question = newQ, correct = a.correct, order = a.order, text = a.text)
				newA.save()
		else:
			q = q.codequestion
			newQ = CodeQuestion(text = q.text, order = q.order, quiz = quiz2, expectedOutput = q.expectedOutput)
			newQ.save()

	quiz2.save()

def matchPath(self, score):
	'''
		This functions takes a quiz and a score and rubs the two together to
		produce the matching path by looking at all of the quizzes paths. A 
		path is matched by lowscore <= score <highscore. If no matching path
		is found, it raises the NoMatchingPath exception

		Parameters:
		   self - the quiz being operated on
		   score - the score, represented as a percentage 0-100

		@author Evan Kleist
	'''
	paths = self.paths.all()

	for p in paths:
		if (score >= p.lowscore and score < p.highscore):
			return p
		if (score == p.highscore and score == 100):
			return p

	raise NoMatchingPath

def editPath(self, request, course_slug):
	'''
		Edits an existing path on a quiz. If this function is called from anything
		other than the Edit Path form, it will result in an exception.

		Parameters:
		   self - the quiz being operated on
		   request - an HttpRequest that contains POST data representing the
		             edited fields of the path. This data is obtained by 
			          the form displayed when the Edit Path button is pressed.
		   course_slug - the course slug for the course that the path belongs to

		@author Evan Kleist
	'''
	errors = []
	path = int(request.POST["path"])
	path = self.paths.get(lowscore=request.POST["path"])

	try:
		lowScore = int(request.POST["LowScore"])
		if (lowScore < 0 or lowScore > 100):
			errors.append("Low Score must be between 0 and 100")

		try:
			matchingPath = matchPath(self, lowScore)
			if (matchingPath != path):
				errors.append("A path that matches this range exists already")
		except NoMatchingPath:
			pass			
	except ValueError:
		lowScore = 0
		errors.append("Low Score must be an integer")

	try:
		highScore = int(request.POST["HighScore"])
		if (highScore < 0 or highScore > 100):
			errors.append("High Score must be between 0 and 100")
		if (highScore < lowScore):
			errors.append("Low Score must be less than or equal too High Score")
	except ValueError:
		errors.append("High Score must be an integer")

	if (path.passed == True and not "passing" in request.POST):
		# Trying to change a path to go from passing to not passing
		# If other quizzes require this quiz as a prerequisite,
		# make sure an alternate passing path is available
		paths = self.paths.all()
		otherPassing = False
		for p in paths:
			if (p.passed and p.lowscore != path.lowscore):
				otherPassing = True
		if (otherPassing == False):
			# No passing path so make sure no quizzes require it as a prerequisite
			course = self.course
			for quiz in course.pages.all():
				try:
					quiz = quiz.quiz
					if (quiz.slug == safeSlug(quiz.slug)):
						prereqs = quiz.prerequisites.all()
						for p in prereqs:
							if (p.requiredQuiz.slug == safeSlug(self.slug)):
								# A quiz requires this quiz as a prerequisite
								# and no pathing pass exists, error
								errors.append(quiz.name + " requires this quiz as a prerequisite and no other passing path exists")
				except Quiz.DoesNotExist:
					pass

	course = Course.objects.get(slug=course_slug)
	if (len(errors) == 0):
		path.lowscore = lowScore
		path.highscore = highScore
		path.toPage = course.pages.get(slug=request.POST["pathPage"])
		path.text = request.POST["dialogue"]
		path.passed = "passing" in request.POST
		path.save()
		publishedCopy = Quiz.objects.get(slug = safeSlug(self.slug), course=course)
		publishedCopy.upToDate = False
		publishedCopy.save()
	
	return errors

def publishQuiz(self):
	''' 
		Publishes the contents of a working copy of a quiz over to the live copy.
		Sets the published copy to be "Up To Date".

		Parameters:
		   self - the quiz being operated on. This can be either the working copy
		          or the published copy and the function will act the exact same

		@author Evan Kleist
	'''
	errors = validateQuiz(self)
	if (len(errors) == 0):
		publishedSlug = safeSlug(self.slug)
		publishedQuiz = Quiz.objects.get(slug=publishedSlug, course=self.course)
		copyQuiz(self, publishedQuiz)
		publishedQuiz.upToDate = True
		publishedQuiz.save()
	return errors

def removePath(self, request):
	'''
		Removes a path from a quiz. If this function is called from anything
		other than the quiz editor form, it will result in an exception.

		Parameters:
		   self - the quiz being operated on
		   request - an HttpRequest that contains POST data representing the
		              path to be removed. This data is obtained by the form
		             displayed when the remove path button is pressed.

		@author Evan Kleist
	'''
	errors = []
	course = self.course
	path = self.paths.get(lowscore = request.POST["path"])
	# See if there is still a passing path
	paths = self.paths.all()
	passingPath = False
	for p in paths:
		if (p.passed == True and not p.lowscore == path.lowscore ):
			passingPath = True
	
	if (passingPath == False):
		# No passing path so make sure no quizzes require it as a prerequisite
		for quiz in course.pages.all():
			try:
				quiz = quiz.quiz
				if (quiz.slug == safeSlug(quiz.slug)):
					prereqs = quiz.prerequisites.all()
					for p in prereqs:
						if (p.requiredQuiz.slug == safeSlug(self.slug)):
							# A quiz requires this quiz as a prerequisite
							# and no pathing pass exists, error
							errors.append(quiz.name + " requires this quiz as a prerequisite and no other passing path exists")
			except Quiz.DoesNotExist:
				pass

	if (len(errors) == 0):
		path.delete()
		publishedCopy = Quiz.objects.get(slug = safeSlug(self.slug), course=course)
		publishedCopy.upToDate = False
		publishedCopy.save()

	return errors

def removeQuiz(self):
	'''
		Removes a quiz from the databass. It will recursivly delete all related
		objects including paths, prerequisites, questions, and answers and the working copy.
		Statistics will be left in the database for data integrity purposes
		but will be unreachable by the program.

		Parameters:
		   self - the quiz being operated on

		@author Evan Kleist
	'''
	questions = self.questions.all()
	prerequisites = self.prerequisites.all()
	paths = self.paths.all()
	workingQuiz = Quiz.objects.get(slug=(self.slug + "_workingCopy"), course=self.course)
	workingQuestions = workingQuiz.questions.all()
	workingPrerequisites = workingQuiz.prerequisites.all()
	workingPaths = workingQuiz.paths.all()

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

	# Remove Paths
	for p in paths:
		p.delete()
	for p in workingPaths:
		p.delete()

	# Remove Pages
	removePage(self)
	workingQuiz.delete()
	# should also remove all associated quiz objects such as stats, questions, answers, paths
	return 0

def reorderQuestions(self):
	'''
		Retreieves a quizzes questions and reorders them into
		a valid state.

		Parameters:
		   self - the quiz being operated on

		@author Evan Kleist
	'''
	questions = self.questions.all().order_by("order")
	qNum = 1
	for q in questions:
		q.order = qNum
		q.save()
		qNum = qNum + 1

def revertQuiz(self):
	'''
		Reverts a working copy of a quiz back to its respective
		published copy. Calling this function on a published copy
		will copy the published copy onto itself, resulting in no
		visible effect.

		Parameters:
		   self - the quiz being operated on

		@author Evan Kleist
	'''
	publishedSlug = safeSlug(self.slug)
	publishedQuiz = Quiz.objects.get(slug=publishedSlug, course=self.course)
	
	copyQuiz(publishedQuiz, self)
	publishedQuiz.upToDate = True
	publishedQuiz.save()


def safeSlug(page_slug):
	'''
		Strips off the trailing "_workingCopy" on a quiz, if it exists. Useful to
		make sure a user isnt trying to directly access a working copy of a quiz.

		Parameters:
		   page_slug - the slug to make "safe"

		@author Evan Kleist
	'''

	if (page_slug.endswith("_workingCopy") != False and page_slug.find("_workingCopy") <= len(page_slug) - 12 and page_slug != "_workingCopy"):
		return page_slug[:-12]

	return page_slug
		

def saveQuiz(request, course_slug, pid):
	'''
		Saves the data contained in the request to the working copy
		of a quiz. Calling this function from anything other than
		the quiz editor form will result in an exception.

		Parameters:
		   request - an HttpRequest that contains POST data representing the
		             quiz to be saved. This data is obtained by the form
		             displayed when the Save button is pressed.
		   course_slug - the course slug for the course that the quiz belongs to
			pid - the page slug for the quiz being worked on

		@author Evan Kleist
	'''
	data = {}
	errors = []
	course = Course.objects.get(slug = course_slug)
	quiz = Page.objects.get(slug=(pid + "_workingCopy"), course=course).quiz
	publishedQuiz = Page.objects.get(slug=pid, course=course).quiz

	# Title - Make sure its not a duplicate in the course
	try:
		quiz2 = Quiz.objects.get(slug=slugify(request.POST["quizTitle"]) + "_workingCopy", course=course)
		if (quiz2.pk != quiz.pk):
			errors.append("Quiz Title already exists!")
	except Quiz.DoesNotExist:
		pass

	# Title - Make sure its not blank
	if (len(request.POST["quizTitle"]) == 0):
		errors.append("Quiz Title cannot be blank!")

	if (len(errors) == 0):
		quiz.text = request.POST["quizTitle"]
		quiz.name = request.POST["quizTitle"]
		publishedQuiz.slug = slugify(quiz.name)
		quiz.slug = publishedQuiz.slug + "_workingCopy"
		quiz.hidden = "hidden" in request.POST
		# Delete current prerequisites
		for p in quiz.prerequisites.all():
			p.delete()
		if "prereqs" in request.POST:
			# Create prerequisites
			for p in request.POST.getlist("prereqs"):
				reqQuiz = Course.objects.get(slug=course_slug).pages.get(slug=p).quiz
				newPrereq = Prerequisite(containingQuiz=quiz, requiredQuiz=reqQuiz)
				newPrereq.save()
			
		questions = quiz.questions.all()
		for q in questions:
			if (isMultipleChoiceQuestion(q)):
				q = q.multiplechoicequestion
				for a in q.answers.all():
					a.text = request.POST['mcq%sa%s' % (q.order, a.order)]
					a.correct = (("mcq%sac" % q.order) in request.POST and request.POST["mcq%sac" % q.order] == str(a.order))
					a.save()
				q.text = request.POST['mcq%stext' % q.order]
				q.order = request.POST['mcq%sorder' % q.order]
			else:
				q = q.codequestion
				q.text = request.POST['cq%stext' % q.order]
				q.expectedOutput = request.POST['cq%seo' % q.order]
				q.order = request.POST['cq%sorder' % q.order]
			q.save()

		publishedQuiz.upToDate = False
		quiz.save()
		publishedQuiz.save()

	data = {"quiz_slug":publishedQuiz.slug, "errors":errors}
	return data

def scoreQuiz(self, request, course_slug, quiz_slug):
	'''
		Pulls the submitted answers from the form contained in the 
		request and compares it to the correct answers specified 
		in the quiz. Generates a statistic for a quiz, adds it 
		to the database and returns their score. Calling this
		function from anything other than the Show Quiz form
		will result in an exception

		Parameters:
		   self - the quiz being operated on
		   request - an HttpRequest that contains POST data representing the
		             answers for the quiz. This data is obtained by the form
		             displayed when a quiz is viewed.
		   course_slug - the course slug for the course that the quiz belongs to
		   quiz_slug - the quiz slug for the quiz being submitted

		@author Evan Kleist
	'''
	questions = self.questions.all()
	course = Course.objects.get(slug=course_slug)
	score = 0

	for q in questions:
		if (isMultipleChoiceQuestion(q)):
			q = q.multiplechoicequestion
			if ('mcq%s' % q.order) in request.POST:
				theirAnswer = request.POST['mcq%s' % q.order]
				if (q.answers.get(order=theirAnswer).correct):
					score = score + 1
		else:
			q = q.codequestion
			theirCode = request.POST['cq%s' % q.order]
			expectedCode = q.expectedOutput
			try:
				(theirResult, scope) = evalPythonString(theirCode)
				(expectedResult, scope) = evalPythonString(expectedCode)
				if (theirResult == expectedResult):
					score = score + 1

			except Exception, e:
				# Something went wrong with their code, could be bad syntax, invalid command, etc
				pass
			

	if (request.user and not request.user.is_anonymous()):
		Stat.CreateStat(course, self, request.user, score)
	
	return score

def validateQuestionOrder(self):
	'''
		Verifies that all of a quizzes questions have a unique ordering, 
		and are ordered from 1 -> # of questions

		Returns True if the above constraints are met, False otherwise

		Parameters:
		   self - the quiz being operated on

		@author Evan Kleist
	'''
	
	questions = self.questions.all()
	usedNumbers = set([question.order for question in questions])
	if (len(questions) == 0):
		return True
	if len(questions) != len(usedNumbers) or \
		min(usedNumbers) != 1 or max(usedNumbers) != len(questions):
			return False
	return True

def validateQuiz(self):
	'''
		Validates a quiz to make sure all of its data is valid. Quiz Title must
		be an string > 0 characters and must not be a duplicate. Any
		prerequisites must have a corresponding passing path, otherwise
		the quiz would be unreachable. All question prompts cannot be blank.
		No answer can be blank. A multiple choice question must have >=
		2 answers and 1 must be correct. Questions must have a valid ordering.

		Parameters:
		   self - the quiz being operated on

		@author Evan Kleist
	'''
	errors = []
	questions = self.questions.all()
	
	# Title - Make sure its not blank
	if (len(self.text) == 0):
		errors.append("Quiz Title can not be blank")

	# Hidden - There can be no errors in this

	# Prerequisites - Make sure the required quiz(s) have a "passing" path
	for prereq in self.prerequisites.all():
		requiredQuiz = prereq.requiredQuiz
		foundPath = False
		for path in requiredQuiz.paths.all():
			if (path.passed == True):
				foundPath = True
		if (foundPath == False):
			errors.append(requiredQuiz.name + " does not have a passing path")

	for q in questions:
		if (isMultipleChoiceQuestion(q)):
			# Multiple Choice Question - Make sure its not blank
			q = q.multiplechoicequestion
			if (len(q.text) == 0):
				errors.append("Question cannot have a blank prompt")

			answers = q.answers.all()
			
			# Question must have at least two possible answers
			if (len(answers) < 2):
				errors.append("Question must have at least two possible answers")

			foundCorrect = False
			for a in answers:
				# Answer must not be blank
				if (len(a.text) == 0):
					errors.append("Answer must not be blank")
				if (a.correct):
					foundCorrect = True

			# Question must have a correct answer
			if (not foundCorrect):
				errors.append("Question must have a correct answer")
		else:
			q = q.codequestion
			
			# Prompt must not be blank
			if (len(q.text) == 0):
				errors.append("Code Question prompt must not be blank")

			# Expected output must not be blank
			if (len(q.expectedOutput) == 0):
				errors.append("Code Question expected output must not be blank")

	# Question Ordering - Must be valid
	if (not validateQuestionOrder(self)):
		errors.append("Questions must have a valid ordering")

	return errors
	
