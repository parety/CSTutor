object Course
	components: p:Page* and r:Roster and privateClass:bool and name:string and chatRoom:string and Stats and text:string*;
	operations: AddPage and RemovePage and SetPrivate and EditCourse;
	description: (* A course is a course. It contains zero or more pages, a course roster, a boolean determining whether or not the course is public or private, a string for the name of the course, a string for the chat room, a Stats object containing all of the course specific statistics, and a string containing a welcome text for the course *);
end Course; 

operation AddPage
end AddPage;

operation RemovePage
end RemovePage;

operation SetPrivate
end SetPrivate;

object Page
	compenents: prevPage:Page and nextPage:Page and prereq:Page*;
	description: (* A Page has a link to the previous and next pages, as well as zero or more Page prerequisites.*); 
end Page;

object Lesson implements Page
	components: text:string* and code:string* and subtopic:Page*;
	operations: AddPage and RemovePage EditLesson;
	description: (* A lesson is a specific type of Page. It contains zero or more text fields, zero or more code fields, and links to any subpages *);
end Lesson;

object Quiz implements Page
	components: Question* and text:string* and title:string and prereq:Page and Path and hidden:boolean;
	operations: AddQuestion and RemoveQuestion and EditQuiz and SubmitAnswers and CheckAnswers;
	description: (* A quiz is a specific type of Page. It contains zero or more Questions, a title string, zero or more text fields. It also contains a link to a Page being required as a prerequisite and a boolean for visibility.*);
end Quiz;

object Question
	componets: text:string* and question:string;
	description: (* A Question is question. It contains a string for the prompt, and a string for the title *);
end Question;

object MultipleChoiceQuestion implements Question
	components: Answer+;
	description: (* A multiple choice question is a specific type of question. It contains a list of possible Answers. *);
end MultipleChoiceQuestion;

object Answer
	componenets: answer:string and correct:boolean;
	description: (* A answer is a possible answer for a multiple choice question. It contains a string for the answer and a boolean determining whether or not the answer is correct.*);
end Answer

object CodeQuestion implements Question
	components: code:string and output:string
	operations: compareOutput;
	description: (* A code question is a specific type of question. It allows for code to be entered which is then ran and the output is compared against predefined output. It contains a string for their code, and a string for the correct output *);
end CodeQuestion;

operation compareOutput
	input: userCode:string and correctOutput:string;
	output: correct: boolean and output:string;
	description: (*This operation takes in a users code snippet, runs it, and compares the output. It returns a boolean whether the output matched, as well as the correct output.*);
end compareOutput;

object Roster
	components: (User, Permissions, Stats)*;
	operations: addUser and deleteUser and editPermissions;
	description: (* A roster keeps track of the permissions and statistics for all associated users. *);
end Roster;

operation editPermissions
	input: user:User and modifiedPermissions:Permissions;
	output: newPermissions:Permissions:
	description: (*This operation takes a user and a set of modified permissions, replaces the old permissions, and returns an updated permissions*)
end editPermissions;

object User
	components: isInstructor:boolean and userName:string and password:string and enrolled:Course* and email:string;
	operations: editProfile;
	description: (* A user contains a boolean determining whether or not the user has instructor permissions, a string for the username, a string for the password, and a list of Courses that the user is enrolled in. Additionally, a user may provide an email address. *);
end User;

operation editProfile
	input: currentProfile:User and modifiedProfile:User;
	output: newProfile:User;
	description: (*This operation takes a users profile and any modifications and merges them together, returning an updated profile*)
end editProfile;

object Permissions
	components: view:boolean and edit:boolean and stats:boolean and manage:boolean;
	description: (* Permissions are a set of booleans that map the permissions for users. The view permission allows the user to view the course material. The edit permission allows the user to edit the course material. The stats permission allows the user to view class-wide statistics and roster. The manage permission allows the user to modify the roster and all associated permissions *);
end Permissions;



OPERATIONS LIST:

Jon - user related

addUser
removeUser
setUserPermissions
updateRoster

Russell 

login
logout

Matt

createCourse
removeCourse
createLesson
removeLesson
removePage

Evan

createQuiz
addQuestion
removeQuestion

James

clearStatistics
displayStats
getStats

operation getNextPage
   inputs: Page;
   outputs: Page;
   description: (*Takes in a Page, and returns the next logical page.*);
end getNextPage;

operation getPrevPage
   inputs: Page;
   outputs: Page;
   description: (*Takes in a Page, and returns the previous logical page.*);
end getPrevPage;

operation displayPage
   inputs: Page;
   outputs: String;
   description:  (*Takes in a page and returns the content to display *);
end displayPage;

operation movePage;
   inputs: Page, Page;
   outputs: bool;
   description: (*Takes in two pages, the page to move and the page to 
                 place the moved page after, and moves the first page to be
                 the "next" of the second Page.  Returns boolean indicating 
                 success *);
end movePage;

//RUSSELL MEZZETTA

operation login
	inputs: username, password, database;
	outputs: ...;
	description: (* Takes in username and password then checks server to see if there is a
						match. If so then it grants access *);
end login;
	
operation logout
	inputs: userdata, database;
	outputs: ...;
	description: (* saves all user data to the server *);
end logout;


//JON INLOES

operation addUser
	components:
	inputs: name:string and roster:Roster;
	outputs: updatedRoster:Roster;
	description: (* addUser adds the given string name into the Roster and produces an updated Roster. *);
end addUser;

operation removeUser
	components:
	inputs: name:string* and roster:Roster;
	outputs: ouputs updatedRoster:Roster;
	description: (* removeUser removes the inputed string names from the roster and produces an updated Roster. *);
end removeUser;

operation setUserPermissions
	components:
	inputs: (name:string and edit:boolean and manage:boolean and states:boolean)*;
	outputs: updatedRoster:Roster;
	description: (* setUserPermissions will take in a list of tuples consisting of a string name, boolean edit, boolean manage, and boolean states and will produce an updated Roster with the new user permissions. *)
end setUserPermissions;

operation updateRoster
	components:
	inputs: roster:Roster
	outputs: updated:roster
	description: (* updateRoster will take in a roster and make the changes to a roster final. *)
end updateRoster;
