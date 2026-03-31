#!/usr/bin/env python3
"""
Standalone Python implementation of the 'Register for a Course' use case
from the Java Course Enrollment System.

This module provides the core functionality to register students for courses
with proper validation including prerequisite checks, capacity limits,
schedule conflicts, and duplicate enrollment prevention.
"""

import json
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class TimeSlot:
    """Represents a scheduled time slot for a course."""
    days: str = ""  # e.g., "MWF" or "TTh"
    start_time: str = ""  # 24-hour format "HH:mm"
    end_time: str = ""  # 24-hour format "HH:mm"

    def overlaps(self, other: 'TimeSlot') -> bool:
        """Returns true if this time slot overlaps with another time slot."""
        if not other or not self.days or not other.days:
            return False
        
        if not self._share_days(self.days, other.days):
            return False
        
        # Convert times to minutes for easy comparison
        this_start = self._to_minutes(self.start_time)
        this_end = self._to_minutes(self.end_time)
        other_start = self._to_minutes(other.start_time)
        other_end = self._to_minutes(other.end_time)
        
        if any(t < 0 for t in [this_start, this_end, other_start, other_end]):
            return False
        
        # Overlap when one interval starts before the other ends
        return this_start < other_end and other_start < this_end

    def _share_days(self, d1: str, d2: str) -> bool:
        """Returns true when two day strings share at least one day."""
        a = d1.upper()
        b = d2.upper()
        
        # Handle common day tokens including "TH" for Thursday
        tokens = ["TH", "M", "T", "W", "F", "S", "U"]
        for token in tokens:
            if token in a and token in b:
                return True
        return False

    def _to_minutes(self, time: str) -> int:
        """Converts 'HH:mm' to total minutes. Returns -1 if format is invalid."""
        if not time or ":" not in time:
            return -1
        try:
            parts = time.split(":")
            return int(parts[0]) * 60 + int(parts[1])
        except (ValueError, IndexError):
            return -1

    def __str__(self) -> str:
        return f"{self.days} {self.start_time}-{self.end_time}"


@dataclass
class Course:
    """Represents a course in the catalog."""
    code: str = ""
    title: str = ""
    credits: int = 0
    capacity: int = 0
    time_slot: Optional[TimeSlot] = None
    prerequisites: List[str] = field(default_factory=list)
    enrolled_students: List[str] = field(default_factory=list)

    def is_full(self) -> bool:
        """Returns true when the course has no remaining spots."""
        return len(self.enrolled_students) >= self.capacity

    def has_student(self, student_id: str) -> bool:
        """Returns true when the given student ID is already enrolled."""
        return student_id in self.enrolled_students

    def enroll_student(self, student_id: str) -> bool:
        """Enrolls a student, returning False if course is full or already enrolled."""
        if self.is_full() or self.has_student(student_id):
            return False
        self.enrolled_students.append(student_id)
        return True

    def remove_student(self, student_id: str) -> bool:
        """Removes a student from this course."""
        try:
            self.enrolled_students.remove(student_id)
            return True
        except ValueError:
            return False

    def get_available_seats(self) -> int:
        """Returns the number of open seats remaining."""
        return max(0, self.capacity - len(self.enrolled_students))

    def __str__(self) -> str:
        prereq_str = ", ".join(self.prerequisites) if self.prerequisites else "None"
        time_str = str(self.time_slot) if self.time_slot else "TBA"
        return (f"{self.code:<10} {self.title:<40} Credits: {self.credits}  "
                f"Capacity: {len(self.enrolled_students)}/{self.capacity}  "
                f"Time: {time_str:<18}  Prerequisites: {prereq_str}")


@dataclass
class Student:
    """Represents a student in the enrollment system."""
    id: str = ""
    name: str = ""
    major: str = ""
    enrolled_courses: List[str] = field(default_factory=list)
    completed_courses: List[str] = field(default_factory=list)

    def is_enrolled_in(self, course_code: str) -> bool:
        """Returns true when the student is enrolled in the given course."""
        return course_code in self.enrolled_courses

    def has_completed(self, course_code: str) -> bool:
        """Returns true when the student has completed the given course."""
        return course_code in self.completed_courses

    def enroll_in(self, course_code: str) -> bool:
        """Adds a course code to the enrolled list."""
        if self.is_enrolled_in(course_code):
            return False
        self.enrolled_courses.append(course_code)
        return True

    def drop_course(self, course_code: str) -> bool:
        """Removes a course code from the enrolled list."""
        try:
            self.enrolled_courses.remove(course_code)
            return True
        except ValueError:
            return False

    def __str__(self) -> str:
        return f"ID: {self.id:<12}  Name: {self.name:<25}  Major: {self.major}"


@dataclass
class EnrollmentResult:
    """Immutable result of an enrollment operation."""
    success: bool
    message: str

    @classmethod
    def success_result(cls, message: str) -> 'EnrollmentResult':
        """Creates a successful enrollment result."""
        return cls(True, message)

    @classmethod
    def failure_result(cls, message: str) -> 'EnrollmentResult':
        """Creates a failed enrollment result."""
        return cls(False, message)


class CourseRegistrationSystem:
    """Core business logic for course registration functionality."""
    
    TUITION_PER_CREDIT = 300.0

    def __init__(self):
        self.students: Dict[str, Student] = {}
        self.courses: Dict[str, Course] = {}

    def add_student(self, student: Student) -> bool:
        """Adds a new student. Returns False if student ID already exists."""
        if not student or student.id in self.students:
            return False
        self.students[student.id] = student
        return True

    def get_student(self, student_id: str) -> Optional[Student]:
        """Returns the student with the given ID, or None if not found."""
        return self.students.get(student_id)

    def add_course(self, course: Course) -> bool:
        """Adds a new course. Returns False if course code already exists."""
        if not course or course.code in self.courses:
            return False
        self.courses[course.code] = course
        return True

    def get_course(self, course_code: str) -> Optional[Course]:
        """Returns the course with the given code, or None if not found."""
        return self.courses.get(course_code)

    def get_all_courses(self) -> List[Course]:
        """Returns all available courses."""
        return list(self.courses.values())

    def register_course(self, student_id: str, course_code: str) -> EnrollmentResult:
        """
        Attempts to register the student in the course.
        
        Performs comprehensive validation including:
        - Student and course existence
        - Duplicate enrollment check
        - Capacity limits
        - Prerequisite requirements
        - Schedule conflicts
        
        Returns an EnrollmentResult indicating success or failure reason.
        """
        # Validate student exists
        student = self.students.get(student_id)
        if not student:
            return EnrollmentResult.failure_result(f"Student not found: {student_id}")

        # Validate course exists
        course = self.courses.get(course_code)
        if not course:
            return EnrollmentResult.failure_result(f"Course not found: {course_code}")

        # Check if already enrolled
        if student.is_enrolled_in(course_code):
            return EnrollmentResult.failure_result(
                f"You are already enrolled in {course_code}."
            )

        # Check course capacity
        if course.is_full():
            return EnrollmentResult.failure_result(
                f"Course {course_code} is full (capacity: {course.capacity})."
            )

        # Check prerequisites
        for prereq in course.prerequisites:
            if not student.has_completed(prereq):
                prereq_course = self.courses.get(prereq)
                prereq_title = prereq_course.title if prereq_course else prereq
                return EnrollmentResult.failure_result(
                    f'Prerequisite not met: you must complete "{prereq_title}" '
                    f'({prereq}) before enrolling in {course_code}.'
                )

        # Check for time conflicts
        if course.time_slot:
            for enrolled_code in student.enrolled_courses:
                enrolled_course = self.courses.get(enrolled_code)
                if (enrolled_course and enrolled_course.time_slot and
                    enrolled_course.time_slot.overlaps(course.time_slot)):
                    return EnrollmentResult.failure_result(
                        f"Schedule conflict: {course_code} ({course.time_slot}) "
                        f"overlaps with {enrolled_code} ({enrolled_course.time_slot})."
                    )

        # All validations passed - perform enrollment
        student.enroll_in(course_code)
        course.enroll_student(student_id)
        
        return EnrollmentResult.success_result(
            f"Successfully enrolled in {course_code} – {course.title}."
        )

    def view_course_catalog(self) -> str:
        """Returns a formatted string of the course catalog."""
        if not self.courses:
            return "No courses available."
        
        output = []
        output.append("=" * 70)
        output.append("  COURSE CATALOG")
        output.append("=" * 70)
        output.append(f"  {'Code':<10} {'Title':<40} {'Credits':<8} {'Seats':<12} {'Time':<18} Prerequisites")
        output.append("  " + "-" * 70)
        
        for course in self.courses.values():
            output.append(f"  {course}")
        
        return "\n".join(output)

    def load_sample_data(self):
        """Loads sample data for testing the registration system."""
        # Add sample courses
        cs101 = Course(
            code="CS101",
            title="Intro to Programming",
            credits=3,
            capacity=30,
            time_slot=TimeSlot("MWF", "09:00", "10:00")
        )
        
        cs201 = Course(
            code="CS201",
            title="Data Structures",
            credits=3,
            capacity=25,
            time_slot=TimeSlot("MWF", "10:00", "11:00"),
            prerequisites=["CS101"]
        )
        
        math101 = Course(
            code="MATH101",
            title="Calculus I",
            credits=4,
            capacity=35,
            time_slot=TimeSlot("MWF", "09:00", "10:00")  # Conflicts with CS101
        )
        
        net101 = Course(
            code="NET101",
            title="Computer Networks",
            credits=3,
            capacity=25,
            time_slot=TimeSlot("TTh", "14:00", "15:30")
        )

        self.add_course(cs101)
        self.add_course(cs201)
        self.add_course(math101)
        self.add_course(net101)

        # Add sample students
        alice = Student("STU001", "Alice Johnson", "Computer Science")
        alice.completed_courses.append("CS101")  # Has prerequisite for CS201
        
        bob = Student("STU002", "Bob Smith", "Mathematics")
        # Bob has no completed courses
        
        self.add_student(alice)
        self.add_student(bob)


def demonstrate_course_registration():
    """Demonstrates the course registration functionality with various scenarios."""
    
    print("=" * 70)
    print("    COURSE REGISTRATION SYSTEM DEMONSTRATION")
    print("=" * 70)
    
    # Initialize system and load sample data
    system = CourseRegistrationSystem()
    system.load_sample_data()
    
    print("\n1. Viewing Course Catalog:")
    print(system.view_course_catalog())
    
    print("\n" + "=" * 70)
    print("2. REGISTRATION SCENARIOS")
    print("=" * 70)
    
    # Test scenarios
    scenarios = [
        ("STU001", "CS201", "Alice registering for CS201 (has CS101 prerequisite)"),
        ("STU002", "CS201", "Bob registering for CS201 (missing CS101 prerequisite)"),
        ("STU001", "CS101", "Alice registering for CS101 (schedule conflict with CS201)"),
        ("STU001", "MATH101", "Alice registering for MATH101 (time conflict with CS101)"),
        ("STU001", "NET101", "Alice registering for NET101 (should succeed)"),
        ("STU001", "NET101", "Alice registering for NET101 again (duplicate enrollment)"),
        ("STU999", "CS101", "Non-existent student registration"),
        ("STU001", "CS999", "Registration for non-existent course")
    ]
    
    for i, (student_id, course_code, description) in enumerate(scenarios, 1):
        print(f"\nScenario {i}: {description}")
        result = system.register_course(student_id, course_code)
        
        status_icon = "[✓]" if result.success else "[✗]"
        print(f"  {status_icon} {result.message}")
        
        # Show current enrollments for existing students
        student = system.get_student(student_id)
        if student:
            enrolled = ", ".join(student.enrolled_courses) if student.enrolled_courses else "None"
            print(f"  Current enrollments for {student.name}: {enrolled}")

    print("\n" + "=" * 70)
    print("3. FINAL COURSE STATUS")
    print("=" * 70)
    
    for course in system.get_all_courses():
        enrolled_count = len(course.enrolled_students)
        students_enrolled = ", ".join(course.enrolled_students) if course.enrolled_students else "None"
        print(f"\n{course.code} - {course.title}")
        print(f"  Enrolled: {enrolled_count}/{course.capacity}")
        print(f"  Students: {students_enrolled}")


def interactive_registration():
    """Provides an interactive interface for course registration."""
    
    system = CourseRegistrationSystem()
    system.load_sample_data()
    
    print("=" * 70)
    print("    INTERACTIVE COURSE REGISTRATION")
    print("=" * 70)
    
    while True:
        print("\nAvailable options:")
        print("  [1] View Course Catalog")
        print("  [2] Register for a Course")
        print("  [3] View Student Info")
        print("  [4] Exit")
        
        choice = input("\nSelect option: ").strip()
        
        if choice == "1":
            print("\n" + system.view_course_catalog())
            
        elif choice == "2":
            print("\n--- Register for a Course ---")
            print(system.view_course_catalog())
            
            student_id = input("\nEnter your Student ID: ").strip()
            if not student_id:
                continue
                
            course_code = input("Enter course code to register: ").strip().upper()
            if not course_code:
                continue
            
            result = system.register_course(student_id, course_code)
            status_icon = "[✓]" if result.success else "[✗]"
            print(f"  {status_icon} {result.message}")
            
        elif choice == "3":
            student_id = input("\nEnter Student ID: ").strip()
            student = system.get_student(student_id)
            
            if student:
                print(f"\nStudent Information:")
                print(f"  {student}")
                enrolled = ", ".join(student.enrolled_courses) if student.enrolled_courses else "None"
                completed = ", ".join(student.completed_courses) if student.completed_courses else "None"
                print(f"  Enrolled Courses: {enrolled}")
                print(f"  Completed Courses: {completed}")
            else:
                print(f"  [!] Student not found: {student_id}")
                
        elif choice == "4":
            print("\nThank you for using the Course Registration System!")
            break
            
        else:
            print("  [!] Invalid option. Please enter 1, 2, 3, or 4.")


if __name__ == "__main__":
    print("Course Registration System - Python Implementation")
    print("Converted from Java Course Enrollment System")
    print("\nChoose demonstration mode:")
    print("  [1] Automated demonstration")
    print("  [2] Interactive mode")
    
    mode = input("\nSelect mode (1 or 2): ").strip()
    
    if mode == "1":
        demonstrate_course_registration()
    elif mode == "2":
        interactive_registration()
    else:
        print("Invalid selection. Running automated demonstration...")
        demonstrate_course_registration()
