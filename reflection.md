# PawPal+ Project Reflection

## 1. System Design

The three core actions a user should be able to preform is creaeting a profile(entering pet info and more), manage task (add, edit and remove care taking task), and generate a plan.

**a. Initial design**

- Briefly describe your initial UML design.
The UML is split into 5 categories: owner, pet, task, plan, constraints. The relationship between the 5 is: Owner -> Pet -> constraints and (plan -> task). And for example, if there are multiple pets then each constraint, plan, and task will be for that pet only.
- What classes did you include, and what responsibilities did you assign to each?
I included the five classes below:
- Owner: human identity, contact info
- Pet: Breed, weight, age, behaviors
- Constraint: rules that a plan must follow for the pet, max daily task, time windows, budget, priority stuff.
- Plan: generating a plan and why certain task were chosen, what a day of taking care of the pet might look like.
- Task: single action item that is in the plan. Ex. Feeding, walking, medicine. 

**b. Design changes**

- Did your design change during implementation?
Yes!
- If yes, describe at least one change and why you made it.
One change wwwas that initially the onwer.pet had no pet list even though the UML edge has Owner -> pet: owns. There were more changes like this. 

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
Some constraints for my scheduler is time. A task is a condidite if its due on the day of the plan and if the pet owner has available time for it. 
- How did you decide which constraints mattered most?
I just thought about what I would like as an owner, as important is the task is, it is not do-able if you are not available!

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
A tradeoff my schedule makes is that if there are two task that overlap in time, the scheduler will flag and warn the user but still keep the task in the plan. Thus, the task does not automatically drop or do anthing. 
- Why is that tradeoff reasonable for this scenario?
I think it is reasonable because the user gets to choose which task to do or how they would like to prioritize the two task.

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
I used AI for all of this. I used it for the UX, brainstorming new algorithim ideas, debugging, and refactoring
- What kinds of prompts or questions were most helpful?
I found the most helpful prompts were specific and with an example, for example "Can you please do ""blank" like "blank"


**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
I did not acceept and AI suggestion when it changed my UMI the second time. 
- How did you evaluate or verify what the AI suggested?
I looked at it on the diagram and thought it looked weird to me so I decided to redo it

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
I tested many things, one being the time conflicts.
- Why were these tests important?
They were important because well I think we should always test AI  and because we want it to make sense to users!
**b. Confidence**

- How confident are you that your scheduler works correctly?
Maybe like a 4
- What edge cases would you test next if you had more time?
If I had more time I would test like a bunch of random test but one being more than 3 conflicts. 

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?
I am satisfied with the outcome. I have never used AI like this with code so I thought it was cool.

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?
Like last time, I ended up rushing so for next time I would love to just slow down and redesign the UIUX to look nicer and easier to navigate

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
I learend that AI is not perfect and you have to redo a lot of things and be very specific!