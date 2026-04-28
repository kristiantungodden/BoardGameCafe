# Group project

As a group you can pick one of the following projects available for the class.

1. [Board game café](boardgame_cafe.md): A system for a fictional board game café where customers reserve tables and borrow games.
2. [Personal finance tracker](finance_tracker.md): A web application that helps users track their personal finances.
3. [Online pub quiz - review roulette](review_roulette.md): A real-time web application where users can join quiz rooms and answer questions about landmarks around the world.
4. [Campus Eats](campus_eats.md): A food delivery service for a campus environment.
5. [Campus Ride](campus_ride.md): A ride-sharing application for a campus environment.

## Common for all projects

### Technology

You are free to use what ever technology you want, within the requirements of the project. That includes languages, but we expect you to write good, maintainable code in whatever language you pick.

This is not a front-end course, but several of the topics we have touched upon makes sense in a front-end context. You are free to build the kind of front-end you want, from a full on SPA to simple HTML pages, but whatever you do, keep it clean, structured and readable.

This is not a design course. You will not be penalized for having an application that looks crap, as long as it's functional. The functionality is the important thing.

### Criteria for judging the delivery

* Does the report show
  * how the team organised their work?
  * what challenges the team had and how they solved them?
  * major decisions that the team made and the reasoning behind them?
  * that the team has reflected on their way of working?
* Separation of concerns. Business logic is clearly separated from infrastructure logic and UI logic.
* Separation of contexts. See what belongs together and keep it together.
* Loosely coupled code. Use things like events and external message bus to make a robust message transfer between the contexts.
* Domain model. The domain here is not big, but the domain objects you have should be clearly defined, well connected and contain the logic required to operate on them.
* Unit tests: Business logic has unit tests
* Integration tests: Infrastructure and side effects are tested
* Code follows a readable and discoverable structure. It is easy to figure out what belongs where and things are where you expect it to be.
* It is easy to clone the project and run it. It should work out of the box, and be able to run with a single command. It should have minimal dependencies for the machine it's running on. Requiring the latest .NET SDK, Node.js or Python installed are reasonable dependencies. Using Docker is encouraged for easier deployment.
* CI set up with GitHub Actions.
* Following general object oriented principles like information hiding, tell - don't ask
* Abstractions - Is it easy to replace the implementation of various infrastructure with with another one?
* Did the team manage to implement an adequate number of features?
* Did the team have a good process in place for tracking work?
* How many of the advanced features were implemented?
* Bare minimum functioning application with basic features will most likely fetch you a C, if you manage to implement a few advanced features well, that could elevate your grade to a B or an A.

## Design document

* Every team has to deliver a design document by **24.03.2026**.
* Design document is not graded but an obligatory deliverable.
* Glenn will explain what is a good design document in one of the lectures.
* One of the lectures will be dedicated to discuss and give feedback on the design document.

## Report

* Report can be written in a Word document or an [overleaf template](https://www.overleaf.com/read/nkhzxdyqhkjn)
* The report can be maximum 10 pages please submit in pdf format only (pdf should be named with your group name in QuickFeed.)
* The report should reflect:
  * The report should emphasize the reasoning behind your choices, not just a description of what you did.
  * Highlight the technical decisions you made, *explain why you chose them*, and reflect on how they aligned with your design document.
  * Reflect on how and why you structured collaboration the way you did, and what impact that had on the project.
  * Discuss how you approached breaking down the project into smaller tasks, and why that structure worked (or didn’t work) for your team.
  * Share insights on how you tracked progress, focusing on what tools or methods supported your workflow best and why.
  * Consider your communication practices—what worked well, what caused friction, and what you learned about effective communication.
  * Reflect on how you paused to evaluate your process along the way: what did you discover about your approach, what changes did you make, and how effective were those changes?
  * Be open about mistakes and setbacks: what went wrong, what you learned from it, how you responded, and how that shaped your project outcomes.

## Groups

* Each Group should have exactly *5 students*. Groups will be self-forming on Discord, but if you don't have a group, let us know and we'll assist. Groups smaller than 5 people should get approval from the lecturer/student assistants.
* Everyone must work in a group since executing a project in a team setting is one of the skills that will be assessed in this course.
* The whole group gets same grade so everyone is collectively responsible for the group's grade.
* Please register your group (choose a group name containing last names of all team members) along with your team members in [QuickFeed](https://uis.itest.run/app/home)
* **Registering your group in QuickFeed is mandatory** and important since it will create a GitHub repository which you must use for storing and maintaining your code.

## Deadline

* Deadline for the project code and the report is **28.04.2026 by 23.59**

## Oral presentation

* 100% of the grade is based on the oral exam and performance in the project (code + report).
* Date of the oral presentation will be announced later, but probably within a week or two after the due date
* More details will follow on actual time of day

