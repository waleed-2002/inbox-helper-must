# What I unlearned

*Draft for contributor review. The examples come from the project record. Edit the first-person reflections to match your own experience before submitting.*

## A working demo is weak evidence

The rule classifier was deterministic and passed its focused tests. It still predicted `other` for every development message and scored 4/20. The tests showed that the rules behaved as written. The candidate examples showed how rarely the rules matched indirect requests and references across sentences. I would now write examples from the task before looking at the implementation, keep a baseline, and use the misses to decide what to build next.

## A better score can hide different failures

The first live Groq run reached 13/20, with six classification calls lost to rate limits. One returned label followed an embedded instruction. Pacing and candidate-text screening were part of the next iteration, which reached 19/20 on the same 20 development messages. Because that set guided the changes, the result tells me how the revised system performed on those examples. For a stronger estimate, I would use a fresh unseen set and report unavailable classifications separately from wrong ones.

## A polished reply can still invent a policy

Two drafts in the paced run sounded professional while inventing restrictions on what recruiters could disclose. Reviewing the saved outputs surfaced the problem. The offline safety recheck withheld those drafts and left 13 available for human review. That changed the question I ask of a draft. I now look for the facts supporting each claim and check whether a recruiter can catch and correct an unsupported statement before it leaves the tool.

## Approval belongs to a revision

The browser test gave me a concrete way to check human review. I could approve a reply, export it, then edit it and verify that the previously approved revision disappeared from export. I would use this workflow again. Give AI bounded implementation tasks, keep the evidence it produces, and independently test the consequences that matter to the person using the tool.
