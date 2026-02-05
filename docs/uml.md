classDiagram

class User {
  +role
}
class StudentProfile
class TeacherProfile

User "1" --> "0..1" StudentProfile
User "1" --> "0..1" TeacherProfile

class ClassRoom
class Course
class TeacherCourseAssignment
class MonthlyGoal

TeacherProfile "1" --> "0..*" TeacherCourseAssignment
ClassRoom "1" --> "0..*" TeacherCourseAssignment
Course "1" --> "0..*" TeacherCourseAssignment
ClassRoom "1" --> "0..*" MonthlyGoal

class ClassSession
class SessionTeacher
class AttendanceToken

ClassRoom "1" --> "0..*" ClassSession
ClassSession "1" --> "0..*" SessionTeacher
TeacherProfile "1" --> "0..*" SessionTeacher
ClassSession "1" --> "0..1" AttendanceToken

class StudentAttendance
class TeacherCheckIn
class AttendanceConfirmation

ClassSession "1" --> "0..*" StudentAttendance
StudentProfile "1" --> "0..*" StudentAttendance

ClassSession "1" --> "0..*" TeacherCheckIn
TeacherProfile "1" --> "0..*" TeacherCheckIn

ClassSession "1" --> "0..*" AttendanceConfirmation
TeacherProfile "1" --> "0..*" AttendanceConfirmation

class ExamRuleStatus
class ExamEntryScan
class MonthlyReturnForm

StudentProfile "1" --> "0..*" ExamRuleStatus
ClassRoom "1" --> "0..*" ExamRuleStatus

ClassSession "1" --> "0..*" ExamEntryScan
StudentProfile "1" --> "0..*" ExamEntryScan

StudentProfile "1" --> "0..*" MonthlyReturnForm

class Speech
class SpeechCorrection
class SpeechCoaching
class SpeechScore
class SpeechPublicationDecision

StudentProfile "1" --> "0..*" Speech
Speech "1" --> "0..1" SpeechCorrection
Speech "1" --> "0..1" SpeechCoaching
Speech "1" --> "0..*" SpeechScore
Speech "1" --> "0..1" SpeechPublicationDecision
TeacherProfile "1" --> "0..*" SpeechScore

class NewsPost
User "1" --> "0..*" NewsPost

class TeacherRemark
class MonthlyStudentReport
StudentProfile "1" --> "0..*" TeacherRemark
TeacherProfile "1" --> "0..*" TeacherRemark
StudentProfile "1" --> "0..*" MonthlyStudentReport

class GateEntry
User "0..1" --> "0..*" GateEntry

class Credential
class AccessPoint
class AccessRule
class AccessLog

User "1" --> "0..*" Credential
ClassRoom "0..1" --> "0..*" AccessPoint
AccessPoint "1" --> "0..*" AccessRule
AccessPoint "1" --> "0..*" AccessLog
User "0..1" --> "0..*" AccessLog
GateEntry "0..1" --> "0..*" AccessLog
