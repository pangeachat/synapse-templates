---
applyTo: "templates/course_invite*"
description: "The student invitation email: which notice it renders, what it says, and why it carries no unsubscribe link."
---

# Course invite email

This template renders the `course_invite/student_invite` notice of the engagement catalog: the email a student gets when a teacher invites them to a course, sent by the Synapse module for both the seat invitation and the per-address join link it sent before seats ([joining courses](../../../.github/.github/instructions/joining-courses.instructions.md), which owns what the invitation is and when it is sent). It names the course and its teacher, carries the course's description and the teacher's note when there is one, and has one button, Join Your Course, which opens the course's class link with the invitation. It uses the [brand email layout](brand-email-layout.instructions.md) and shows no unsubscribe link, because an invitation is not yet refusable: the student has no relationship with Pangea to end until they accept. `notices.json` lists it with the other emails this repo renders so the engagement workspace can preview it.
