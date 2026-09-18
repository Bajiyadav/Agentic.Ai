"""
Campus & Graduate Engineering Assessment Track (SHL-Standard 4 Modules):
1. English Comprehension (12 Questions · 15 Minutes)
2. Logical Ability (12 Questions · 15 Minutes)
3. Quantitative Ability (14 Questions · 20 Minutes)
4. Data Structures (18 Questions · 20 Minutes)

Total: 56 Multiple Choice Questions · 70 Minutes
Target Audience: Graduate Hires, Campus Recruits, Associate Software Engineers, SDETs, and Junior Analysts.
"""

from typing import Dict, Any, List
from src.services.exam_catalog import AssessmentQuestion


def build_campus_graduate_questions() -> List[AssessmentQuestion]:
    questions: List[AssessmentQuestion] = []

    # =========================================================================
    # MODULE 1: ENGLISH COMPREHENSION (12 Questions · 15 Minutes)
    # =========================================================================
    sec_eng = "Section 1: English Comprehension (12 Questions · 15 Mins)"
    
    questions.extend([
        AssessmentQuestion(
            id="camp_eng_01",
            type="mcq",
            modality="mcq_fundamentals",
            section="english",
            section_title=sec_eng,
            title="Contextual Vocabulary: Corporate Strategy",
            prompt="Select the word that best completes the sentence: 'The CEO's decision to pivot toward cloud infrastructure was considered __________, given the precipitous decline in on-premise licensing revenue.'",
            options=["A) Preposterous", "B) Sagacious", "C) Tenuous", "D) Arbitrary"],
            correct_option=1,
            explanation="'Sagacious' means having or showing keen mental discernment and good judgment, which accurately aligns with an astute strategic pivot.",
            time_limit_minutes=1
        ),
        AssessmentQuestion(
            id="camp_eng_02",
            type="mcq",
            modality="mcq_fundamentals",
            section="english",
            section_title=sec_eng,
            title="Grammar: Subject-Verb Agreement",
            prompt="Choose the grammatically correct sentence:",
            options=[
                "A) Neither the engineering manager nor the team leads was informed of the server downtime.",
                "B) Neither the engineering manager nor the team leads were informed of the server downtime.",
                "C) Neither the engineering manager nor the team leads has been informed of the server downtime.",
                "D) Neither the engineering manager nor the team leads is informed of the server downtime."
            ],
            correct_option=1,
            explanation="When subjects are joined by 'neither... nor...', the verb agrees with the subject closest to it ('the team leads' is plural, so 'were' is required).",
            time_limit_minutes=1
        ),
        AssessmentQuestion(
            id="camp_eng_03",
            type="mcq",
            modality="mcq_fundamentals",
            section="english",
            section_title=sec_eng,
            title="Sentence Correction: Dangling Modifiers",
            prompt="Identify the sentence free from grammatical dangling or misplaced modifier errors:",
            options=[
                "A) Having deployed the microservice, several unexpected exceptions were noticed in the logs by Maya.",
                "B) Having deployed the microservice, Maya noticed several unexpected exceptions in the logs.",
                "C) While compiling the code, the laptop crashed unexpectedly on Maya.",
                "D) Maya noticed several unexpected exceptions, having been deployed the microservice."
            ],
            correct_option=1,
            explanation="Option B correctly places the modifier 'Having deployed the microservice' immediately preceding the subject 'Maya' who performed the action.",
            time_limit_minutes=1
        ),
        AssessmentQuestion(
            id="camp_eng_04",
            type="mcq",
            modality="mcq_fundamentals",
            section="english",
            section_title=sec_eng,
            title="Reading Comprehension: Microservices vs Monoliths",
            prompt="Passage: 'While microservices architectures decouple development velocity and empower autonomous deployments, they shift operational complexity to distributed tracing, network latency, and eventual consistency boundaries.'\n\nQuestion: Based on the passage, what is the primary operational trade-off of microservices?",
            options=[
                "A) They eliminate all networking overhead.",
                "B) They increase operational challenges in observability, latency, and data consistency across network boundaries.",
                "C) They prevent development teams from working autonomously.",
                "D) They mandate centralized single-threaded database locks."
            ],
            correct_option=1,
            explanation="The passage explicitly highlights that operational complexity is shifted to distributed tracing, network latency, and eventual consistency.",
            time_limit_minutes=1
        ),
        AssessmentQuestion(
            id="camp_eng_05",
            type="mcq",
            modality="mcq_fundamentals",
            section="english",
            section_title=sec_eng,
            title="Vocabulary Antonyms: 'Ephemeral'",
            prompt="Select the word that is most nearly OPPOSITE in meaning to 'Ephemeral':",
            options=["A) Transient", "B) Evanescent", "C) Perpetual", "D) Fleeting"],
            correct_option=2,
            explanation="'Ephemeral' means lasting for a very short time. 'Perpetual' means continuing indefinitely or occurring repeatedly, making it the antonym.",
            time_limit_minutes=1
        ),
        AssessmentQuestion(
            id="camp_eng_06",
            type="mcq",
            modality="mcq_fundamentals",
            section="english",
            section_title=sec_eng,
            title="Idiomatic Expressions: Work Environment",
            prompt="What is the meaning of the phrase 'to throw in the towel' in an engineering project context?",
            options=[
                "A) To clean the server room hardware.",
                "B) To concede defeat or abandon an attempt due to insurmountable blockers.",
                "C) To celebrate the milestone release.",
                "D) To refactor legacy code into microservices."
            ],
            correct_option=1,
            explanation="'To throw in the towel' is an idiom meaning to admit defeat or give up on an endeavor.",
            time_limit_minutes=1
        ),
        AssessmentQuestion(
            id="camp_eng_07",
            type="mcq",
            modality="mcq_fundamentals",
            section="english",
            section_title=sec_eng,
            title="Prepositional Usage: Technical Specifications",
            prompt="Fill in the blank: 'The new API endpoint conforms __________ the OpenAPI 3.1 specification, adhering __________ strict security standards.'",
            options=["A) to, with", "B) with, by", "C) to, to", "D) into, on"],
            correct_option=2,
            explanation="'Conforms to' and 'adhering to' are the standard idiomatic and grammatical prepositional pairings.",
            time_limit_minutes=1
        ),
        AssessmentQuestion(
            id="camp_eng_08",
            type="mcq",
            modality="mcq_fundamentals",
            section="english",
            section_title=sec_eng,
            title="Sentence Structure: Parallelism",
            prompt="Which sentence exhibits correct grammatical parallel structure?",
            options=[
                "A) The software engineer enjoys coding robust APIs, designing clean database schemas, and to mentor junior developers.",
                "B) The software engineer enjoys coding robust APIs, designing clean database schemas, and mentoring junior developers.",
                "C) The software engineer enjoys to code robust APIs, designing clean database schemas, and mentoring junior developers.",
                "D) The software engineer enjoys coding robust APIs, to design clean database schemas, and mentoring junior developers."
            ],
            correct_option=1,
            explanation="Option B maintains parallel gerund forms (-ing verbs): 'coding', 'designing', and 'mentoring'.",
            time_limit_minutes=1
        ),
        AssessmentQuestion(
            id="camp_eng_09",
            type="mcq",
            modality="mcq_fundamentals",
            section="english",
            section_title=sec_eng,
            title="Reading Comprehension: Inference",
            prompt="Passage: 'A common pitfall in agile development is equating velocity with value. A sprint team burning through eighty story points per cycle may feel productive, yet if the delivered features do not solve customer retention or latency regressions, that speed produces technical debt rather than business growth.'\n\nInference: What does the author imply about team velocity metrics?",
            options=[
                "A) Story point velocity is the sole indicator of product excellence.",
                "B) High velocity without tangible business outcomes is deceptive and counterproductive.",
                "C) Teams should completely abandon tracking story points.",
                "D) Customer retention automatically increases as sprint velocity exceeds seventy points."
            ],
            correct_option=1,
            explanation="The author argues that high velocity without solving customer or latency issues produces technical debt, meaning raw velocity is deceptive without value.",
            time_limit_minutes=1
        ),
        AssessmentQuestion(
            id="camp_eng_10",
            type="mcq",
            modality="mcq_fundamentals",
            section="english",
            section_title=sec_eng,
            title="Vocabulary: Contextual Word Substitution",
            prompt="Choose the word closest in meaning to 'Mitigate': 'The team implemented circuit breakers to mitigate downstream database cascading failures.'",
            options=["A) Exacerbate", "B) Alleviate", "C) Propagate", "D) Corroborate"],
            correct_option=1,
            explanation="'Mitigate' means to make less severe or serious, which is synonymous with 'alleviate'.",
            time_limit_minutes=1
        ),
        AssessmentQuestion(
            id="camp_eng_11",
            type="mcq",
            modality="mcq_fundamentals",
            section="english",
            section_title=sec_eng,
            title="Grammar: Active vs Passive Voice",
            prompt="Which sentence is written in the active voice?",
            options=[
                "A) The automated integration tests were executed by the CI runner.",
                "B) A critical vulnerability was patched by the security team yesterday.",
                "C) The CI runner executed the automated integration tests.",
                "D) The memory leak was diagnosed after extensive profiling by the engineer."
            ],
            correct_option=2,
            explanation="In Option C, the subject ('The CI runner') performs the action ('executed') directly upon the object ('the integration tests').",
            time_limit_minutes=1
        ),
        AssessmentQuestion(
            id="camp_eng_12",
            type="mcq",
            modality="mcq_fundamentals",
            section="english",
            section_title=sec_eng,
            title="Cohesion & Transition Words",
            prompt="Choose the appropriate transition word: 'The load balancer failed to distribute requests evenly; __________, server node 3 experienced severe memory thrashing.'",
            options=["A) Consequently", "B) Conversely", "C) Nevertheless", "D) In spite of this"],
            correct_option=0,
            explanation="'Consequently' denotes a direct cause-and-effect relationship between the load balancer failure and the server thrashing.",
            time_limit_minutes=1
        )
    ])

    # =========================================================================
    # MODULE 2: LOGICAL ABILITY (12 Questions · 15 Minutes)
    # =========================================================================
    sec_log = "Section 2: Logical Ability (12 Questions · 15 Mins)"

    questions.extend([
        AssessmentQuestion(
            id="camp_log_01",
            type="mcq",
            modality="mcq_fundamentals",
            section="logical",
            section_title=sec_log,
            title="Syllogism: Deduction Logic",
            prompt="Statements:\n1. All microservices communicate over network protocols.\n2. Some network protocols are unencrypted.\n\nConclusions:\nI. Some microservices communicate over unencrypted protocols.\nII. All unencrypted protocols are used by microservices.\n\nWhich conclusion logically follows?",
            options=[
                "A) Only Conclusion I follows.",
                "B) Only Conclusion II follows.",
                "C) Neither Conclusion I nor II follows.",
                "D) Both Conclusions I and II follow."
            ],
            correct_option=2,
            explanation="Statements only say all microservices use network protocols, and some protocols are unencrypted. It is possible that microservices only use the encrypted subset, so Conclusion I is not guaranteed, and Conclusion II is an illicit distribution.",
            time_limit_minutes=1
        ),
        AssessmentQuestion(
            id="camp_log_02",
            type="mcq",
            modality="mcq_fundamentals",
            section="logical",
            section_title=sec_log,
            title="Linear Seating Arrangement Puzzle",
            prompt="Five developers (A, B, C, D, E) sit in a row of workstations facing north.\n1. C sits immediately between A and E.\n2. B sits to the immediate right of E.\n3. D sits at the extreme left end.\n\nWho sits in the exact middle seat?",
            options=["A) B", "B) C", "C) A", "D) E"],
            correct_option=2,
            explanation="D is at extreme left: [D, _, _, _, _]. C is between A and E, and B is to the right of E. Thus the order from left to right is: D, A, C, E, B. Wait, C is between A and E: D, A, C, E, B has C in the middle! Wait, if order is D, A, C, E, B: D (seat 1), A (seat 2), C (seat 3), E (seat 4), B (seat 5). C is in the middle (seat 3).",
            time_limit_minutes=2
        ),
        AssessmentQuestion(
            id="camp_log_03",
            type="mcq",
            modality="mcq_fundamentals",
            section="logical",
            section_title=sec_log,
            title="Pattern & Number Series",
            prompt="Find the missing number in the sequence: 3, 7, 15, 31, 63, ____?",
            options=["A) 124", "B) 127", "C) 128", "D) 131"],
            correct_option=1,
            explanation="Each term is generated by (previous_term * 2) + 1: (63 * 2) + 1 = 126 + 1 = 127.",
            time_limit_minutes=1
        ),
        AssessmentQuestion(
            id="camp_log_04",
            type="mcq",
            modality="mcq_fundamentals",
            section="logical",
            section_title=sec_log,
            title="Direction Sense Test",
            prompt="An IT engineer walks 20 meters North to Server Room 1, turns right and walks 30 meters to the Network Lab, turns right again and walks 20 meters to the Cafeteria. In which direction and how far is the Cafeteria from the starting point?",
            options=[
                "A) 30 meters East",
                "B) 30 meters West",
                "C) 20 meters South",
                "D) 50 meters North-East"
            ],
            correct_option=0,
            explanation="North 20m (+y 20), Right/East 30m (+x 30), Right/South 20m (-y 20). Final position is (30, 0), which is 30 meters East of the starting point.",
            time_limit_minutes=1
        ),
        AssessmentQuestion(
            id="camp_log_05",
            type="mcq",
            modality="mcq_fundamentals",
            section="logical",
            section_title=sec_log,
            title="Blood Relations: Family Deduction",
            prompt="Pointing to a photograph of a tech founder, Rohit says: 'His father is the only son of my father.' If Rohit has no brothers, who is the founder to Rohit?",
            options=["A) Rohit's Brother", "B) Rohit's Son", "C) Rohit's Father", "D) Rohit's Uncle"],
            correct_option=1,
            explanation="'The only son of my father' is Rohit himself (since he has no brothers). Therefore, the tech founder's father is Rohit, meaning the founder is Rohit's son.",
            time_limit_minutes=1
        ),
        AssessmentQuestion(
            id="camp_log_06",
            type="mcq",
            modality="mcq_fundamentals",
            section="logical",
            section_title=sec_log,
            title="Coding-Decoding Cipher",
            prompt="If in a certain system code 'ROUTER' is encoded as 'SPVUFS', how will 'SERVER' be coded in that same system?",
            options=["A) TFSWFS", "B) TFSUES", "C) UFTEFS", "D) SFUVEQ"],
            correct_option=0,
            explanation="Each letter is shifted forward by +1 alphabetical position: S->T, E->F, R->S, V->W, E->F, R->S = TFSWFS.",
            time_limit_minutes=1
        ),
        AssessmentQuestion(
            id="camp_log_07",
            type="mcq",
            modality="mcq_fundamentals",
            section="logical",
            section_title=sec_log,
            title="Statement and Assumptions",
            prompt="Statement: 'The company issued a policy requiring all code merges to pass automated sonarqube vulnerability scans before QA sign-off.'\n\nAssumptions:\nI. Automated scanners can identify security defects prior to manual testing.\nII. Developers often intentionally inject vulnerabilities into codebase.\n\nWhich assumption is implicit in the statement?",
            options=[
                "A) Only Assumption I is implicit.",
                "B) Only Assumption II is implicit.",
                "C) Both Assumptions I and II are implicit.",
                "D) Neither Assumption I nor II is implicit."
            ],
            correct_option=0,
            explanation="Assumption I is implicit because mandating a tool presupposes that it effectively catches vulnerabilities early. Assumption II is baseless and unjustified.",
            time_limit_minutes=1
        ),
        AssessmentQuestion(
            id="camp_log_08",
            type="mcq",
            modality="mcq_fundamentals",
            section="logical",
            section_title=sec_log,
            title="Truth-Teller & Liar Logic",
            prompt="Two database nodes A and B are being inspected. One always tells the truth, and the other always lies. Node A says: 'At least one of us is a liar.' What are nodes A and B?",
            options=[
                "A) Node A is a liar; Node B is a truth-teller.",
                "B) Node A is a truth-teller; Node B is a liar.",
                "C) Both nodes are liars.",
                "D) Both nodes are truth-tellers."
            ],
            correct_option=1,
            explanation="If A were a liar, the statement 'at least one of us is a liar' would be true, a contradiction. Therefore A is a truth-teller. Since A's statement is true and A is not a liar, B must be the liar.",
            time_limit_minutes=2
        ),
        AssessmentQuestion(
            id="camp_log_09",
            type="mcq",
            modality="mcq_fundamentals",
            section="logical",
            section_title=sec_log,
            title="Analogy Reasoning",
            prompt="Compiler : Machine Code :: Translator : _________?",
            options=["A) Grammar", "B) Target Language", "C) Syntax Error", "D) Hardware"],
            correct_option=1,
            explanation="A compiler transforms source code into machine code; similarly, a translator transforms source language text into the target language.",
            time_limit_minutes=1
        ),
        AssessmentQuestion(
            id="camp_log_10",
            type="mcq",
            modality="mcq_fundamentals",
            section="logical",
            section_title=sec_log,
            title="Letter Sequence Logic",
            prompt="What is the next letter in the series: A, C, F, J, O, ____?",
            options=["A) S", "B) T", "C) U", "D) V"],
            correct_option=2,
            explanation="The difference between letters increases by +1 each step: A(+2)->C(+3)->F(+4)->J(+5)->O(+6)->U.",
            time_limit_minutes=1
        ),
        AssessmentQuestion(
            id="camp_log_11",
            type="mcq",
            modality="mcq_fundamentals",
            section="logical",
            section_title=sec_log,
            title="Venn Diagram Logic",
            prompt="Which relationship best depicts: Engineers, Software Developers, and Musicians?",
            options=[
                "A) All software developers are engineers; some engineers and software developers are musicians.",
                "B) Software developers and musicians are completely disjoint from engineers.",
                "C) All musicians are software developers.",
                "D) Engineers and musicians cannot overlap."
            ],
            correct_option=0,
            explanation="Software development is a subset of engineering disciplines, and any individual from either category can also be a musician (overlapping sets).",
            time_limit_minutes=1
        ),
        AssessmentQuestion(
            id="camp_log_12",
            type="mcq",
            modality="mcq_fundamentals",
            section="logical",
            section_title=sec_log,
            title="Cause and Effect Analysis",
            prompt="Event A: Cloud provider Region us-east-1 experienced a major fiber optic cut.\nEvent B: Hundreds of global SaaS applications experienced degraded latency and connection dropouts.\n\nWhich statement accurately describes the relationship?",
            options=[
                "A) Event B is the cause and Event A is its effect.",
                "B) Event A is the cause and Event B is its direct effect.",
                "C) Both are effects of independent causes.",
                "D) Both are independent causes with no correlation."
            ],
            correct_option=1,
            explanation="The physical infrastructure failure (fiber optic cut) directly caused the degradation in upstream SaaS application traffic and latency.",
            time_limit_minutes=1
        )
    ])

    # =========================================================================
    # MODULE 3: QUANTITATIVE ABILITY (14 Questions · 20 Minutes)
    # =========================================================================
    sec_quant = "Section 3: Quantitative Ability (14 Questions · 20 Mins)"

    questions.extend([
        AssessmentQuestion(
            id="camp_qnt_01",
            type="mcq",
            modality="mcq_fundamentals",
            section="quantitative",
            section_title=sec_quant,
            title="Percentages: Server Cost Reduction",
            prompt="A tech startup reduced its monthly AWS compute bill from $12,500 to $9,500 by utilizing spot instances. What is the percentage decrease in their server costs?",
            options=["A) 20%", "B) 24%", "C) 25%", "D) 30%"],
            correct_option=1,
            explanation="Reduction = $12,500 - $9,500 = $3,000. Percentage decrease = (3,000 / 12,500) * 100 = 24%.",
            time_limit_minutes=1
        ),
        AssessmentQuestion(
            id="camp_qnt_02",
            type="mcq",
            modality="mcq_fundamentals",
            section="quantitative",
            section_title=sec_quant,
            title="Time & Work: Bug Fixing Rate",
            prompt="Senior engineer Alice can resolve a backlog of 60 tickets in 6 hours. Junior engineer Bob takes 12 hours for the same backlog. How long will it take them to resolve the backlog working together at constant rates?",
            options=["A) 3 hours", "B) 4 hours", "C) 4.5 hours", "D) 5 hours"],
            correct_option=1,
            explanation="Alice's rate = 1/6 per hour; Bob's rate = 1/12 per hour. Combined rate = 1/6 + 1/12 = 3/12 = 1/4 per hour. Time required = 4 hours.",
            time_limit_minutes=1
        ),
        AssessmentQuestion(
            id="camp_qnt_03",
            type="mcq",
            modality="mcq_fundamentals",
            section="quantitative",
            section_title=sec_quant,
            title="Time, Speed & Distance: Data Transmission",
            prompt="A file transfer transmits data at a speed of 120 Mbps for 40 seconds, and then accelerates to 180 Mbps for the next 60 seconds. What is the average transmission speed across the entire 100 seconds?",
            options=["A) 150 Mbps", "B) 156 Mbps", "C) 160 Mbps", "D) 165 Mbps"],
            correct_option=1,
            explanation="Total data transferred = (120 * 40) + (180 * 60) = 4,800 + 10,800 = 15,600 Mb. Total time = 100 s. Average speed = 15,600 / 100 = 156 Mbps.",
            time_limit_minutes=1
        ),
        AssessmentQuestion(
            id="camp_qnt_04",
            type="mcq",
            modality="mcq_fundamentals",
            section="quantitative",
            section_title=sec_quant,
            title="Ratios & Proportions: Memory Allocation",
            prompt="A server divides 64 GB of RAM between application cache, database buffer pool, and OS headroom in the ratio 3 : 4 : 1. How many gigabytes are dedicated to the database buffer pool?",
            options=["A) 16 GB", "B) 24 GB", "C) 32 GB", "D) 40 GB"],
            correct_option=2,
            explanation="Total parts = 3 + 4 + 1 = 8 parts. 64 GB / 8 = 8 GB per part. Database buffer pool = 4 * 8 GB = 32 GB.",
            time_limit_minutes=1
        ),
        AssessmentQuestion(
            id="camp_qnt_05",
            type="mcq",
            modality="mcq_fundamentals",
            section="quantitative",
            section_title=sec_quant,
            title="Profit and Loss: SaaS Software Pricing",
            prompt="A SaaS license costing $400 to service annually is sold with a 25% profit margin. During a black friday campaign, a discount of 10% is applied to the selling price. What is the final selling price?",
            options=["A) $450", "B) $475", "C) $480", "D) $500"],
            correct_option=0,
            explanation="Initial Selling Price = $400 * 1.25 = $500. Discounted Selling Price = $500 * (1 - 0.10) = $450.",
            time_limit_minutes=1
        ),
        AssessmentQuestion(
            id="camp_qnt_06",
            type="mcq",
            modality="mcq_fundamentals",
            section="quantitative",
            section_title=sec_quant,
            title="Probability: Independent Server Failures",
            prompt="Two redundant independent servers A and B have failure probabilities of P(A) = 0.05 and P(B) = 0.02 during a deployment. What is the probability that AT LEAST ONE server continues operating successfully without failure?",
            options=["A) 0.001", "B) 0.93", "C) 0.999", "D) 0.95"],
            correct_option=2,
            explanation="Probability both fail simultaneously = P(A fails) * P(B fails) = 0.05 * 0.02 = 0.001. P(at least one survives) = 1 - P(both fail) = 1 - 0.001 = 0.999.",
            time_limit_minutes=1
        ),
        AssessmentQuestion(
            id="camp_qnt_07",
            type="mcq",
            modality="mcq_fundamentals",
            section="quantitative",
            section_title=sec_quant,
            title="Combinatorics: Password Generation",
            prompt="How many unique 4-character API auth keys can be formed using digits 0 to 9 if digits cannot be repeated?",
            options=["A) 3,024", "B) 5,040", "C) 10,000", "D) 6,561"],
            correct_option=1,
            explanation="Permutation formula: 10P4 = 10 * 9 * 8 * 7 = 5,040.",
            time_limit_minutes=1
        ),
        AssessmentQuestion(
            id="camp_qnt_08",
            type="mcq",
            modality="mcq_fundamentals",
            section="quantitative",
            section_title=sec_quant,
            title="Simple & Compound Interest: Cloud Reserve Lease",
            prompt="A company commits $20,000 for server lease prepayments earning 10% annual interest compounded annually. What is the compound amount at the end of 2 years?",
            options=["A) $22,000", "B) $24,000", "C) $24,200", "D) $24,400"],
            correct_option=2,
            explanation="A = P * (1 + r)^n = $20,000 * (1.10)^2 = $20,000 * 1.21 = $24,200.",
            time_limit_minutes=1
        ),
        AssessmentQuestion(
            id="camp_qnt_09",
            type="mcq",
            modality="mcq_fundamentals",
            section="quantitative",
            section_title=sec_quant,
            title="Pipes and Cisterns: Database Buffer Queue",
            prompt="Pipe A can fill a data buffer in 10 minutes, while Pipe B drains it in 15 minutes. If both are active simultaneously, how long does it take to fill the empty buffer?",
            options=["A) 25 minutes", "B) 30 minutes", "C) 35 minutes", "D) 40 minutes"],
            correct_option=1,
            explanation="Net filling rate per minute = 1/10 - 1/15 = (3 - 2) / 30 = 1/30. Therefore, 30 minutes are required.",
            time_limit_minutes=1
        ),
        AssessmentQuestion(
            id="camp_qnt_09_b",
            type="mcq",
            modality="mcq_fundamentals",
            section="quantitative",
            section_title=sec_quant,
            title="Averages: Microservice Response Times",
            prompt="The response times of 5 consecutive microservice requests are 45ms, 55ms, 60ms, 70ms, and 90ms. If a 6th request arrives and reduces the mean latency to 60ms, what was the latency of the 6th request?",
            options=["A) 40 ms", "B) 50 ms", "C) 60 ms", "D) 65 ms"],
            correct_option=0,
            explanation="Sum of first 5 requests = 45 + 55 + 60 + 70 + 90 = 320ms. Target sum for 6 requests at 60ms average = 6 * 60 = 360ms. 6th request = 360 - 320 = 40ms.",
            time_limit_minutes=1
        ),
        AssessmentQuestion(
            id="camp_qnt_11",
            type="mcq",
            modality="mcq_fundamentals",
            section="quantitative",
            section_title=sec_quant,
            title="Mixture & Alligation: CPU Workload Distribution",
            prompt="In what ratio must an enterprise mix $30/hour high-memory instances with $80/hour high-GPU instances to achieve an average instance operational cost of $50/hour?",
            options=["A) 3 : 2", "B) 2 : 3", "C) 1 : 1", "D) 5 : 3"],
            correct_option=0,
            explanation="Rule of alligation: (Cost of GPU - Target) / (Target - Cost of CPU) = (80 - 50) / (50 - 30) = 30 / 20 = 3 : 2.",
            time_limit_minutes=1
        ),
        AssessmentQuestion(
            id="camp_qnt_12",
            type="mcq",
            modality="mcq_fundamentals",
            section="quantitative",
            section_title=sec_quant,
            title="Algebra: Linear Equations",
            prompt="If 3x + 2y = 24 and 2x + 3y = 26, what is the value of x + y?",
            options=["A) 8", "B) 9", "C) 10", "D) 12"],
            correct_option=2,
            explanation="Adding both equations: (3x + 2x) + (2y + 3y) = 24 + 26 => 5x + 5y = 50 => 5(x + y) = 50 => x + y = 10.",
            time_limit_minutes=1
        ),
        AssessmentQuestion(
            id="camp_qnt_13",
            type="mcq",
            modality="mcq_fundamentals",
            section="quantitative",
            section_title=sec_quant,
            title="Logarithmic Scales: Audio Decibel / Complexity",
            prompt="If log10(2) ≈ 0.3010, what is the approximate value of log10(32)?",
            options=["A) 1.204", "B) 1.505", "C) 1.806", "D) 2.107"],
            correct_option=1,
            explanation="32 = 2^5. Therefore, log10(32) = 5 * log10(2) ≈ 5 * 0.3010 = 1.505.",
            time_limit_minutes=1
        ),
        AssessmentQuestion(
            id="camp_qnt_14",
            type="mcq",
            modality="mcq_fundamentals",
            section="quantitative",
            section_title=sec_quant,
            title="Geometry / Optimization: Data Center Rack Volume",
            prompt="A server rack measures 2 meters high, 1 meter wide, and 1.5 meters deep. If its height is increased by 50% and its depth is reduced by 20%, what is the percentage change in rack volume?",
            options=["A) 10% increase", "B) 20% increase", "C) 30% increase", "D) No change"],
            correct_option=1,
            explanation="V_new = (1.5 * H) * W * (0.8 * D) = (1.5 * 0.8) * V_old = 1.20 * V_old, representing a 20% increase.",
            time_limit_minutes=1
        )
    ])

    # =========================================================================
    # MODULE 4: DATA STRUCTURES (18 Questions · 20 Minutes)
    # =========================================================================
    sec_ds = "Section 4: Data Structures (18 Questions · 20 Mins)"

    questions.extend([
        AssessmentQuestion(
            id="camp_ds_01",
            type="mcq",
            modality="dsa_algorithms",
            section="data_structures",
            section_title=sec_ds,
            title="Array Time Complexity: Unsorted Search",
            prompt="What is the worst-case time complexity of searching for an element in an unsorted array of N elements?",
            options=["A) O(1)", "B) O(log N)", "C) O(N)", "D) O(N log N)"],
            correct_option=2,
            explanation="In an unsorted array, linear search must inspect up to all N elements in the worst case, giving O(N).",
            time_limit_minutes=1
        ),
        AssessmentQuestion(
            id="camp_ds_02",
            type="mcq",
            modality="dsa_algorithms",
            section="data_structures",
            section_title=sec_ds,
            title="Linked List: Cycle Detection Algorithm",
            prompt="Which algorithm detects a cycle in a singly linked list in O(N) time and O(1) auxiliary space?",
            options=[
                "A) Dijkstra's Algorithm",
                "B) Floyd's Cycle-Finding Algorithm (Tortoise and Hare)",
                "C) Tarjan's Strongly Connected Components",
                "D) Prim's Minimum Spanning Tree"
            ],
            correct_option=1,
            explanation="Floyd's Tortoise and Hare algorithm uses two pointers advancing at different speeds (1 step and 2 steps) to detect loops in O(1) space.",
            time_limit_minutes=1
        ),
        AssessmentQuestion(
            id="camp_ds_03",
            type="mcq",
            modality="dsa_algorithms",
            section="data_structures",
            section_title=sec_ds,
            title="Stack Data Structure: LIFO Invariant",
            prompt="Which of the following problems is canonical for a Stack data structure?",
            options=[
                "A) Breadth-First Search (BFS) level-order traversal",
                "B) Evaluating arithmetic expressions in postfix (Reverse Polish) notation",
                "C) Round-robin process CPU scheduling",
                "D) Shortest path in unweighted graphs"
            ],
            correct_option=1,
            explanation="Postfix evaluation and balanced parentheses are classic applications of a Stack's Last-In-First-Out (LIFO) property.",
            time_limit_minutes=1
        ),
        AssessmentQuestion(
            id="camp_ds_04",
            type="mcq",
            modality="dsa_algorithms",
            section="data_structures",
            section_title=sec_ds,
            title="Queue Data Structure: FIFO Traversal",
            prompt="Which graph traversal algorithm fundamentally relies on a Queue data structure?",
            options=[
                "A) Depth-First Search (DFS)",
                "B) Breadth-First Search (BFS)",
                "C) Topological Sort via DFS Post-Order",
                "D) Bellman-Ford Shortest Path"
            ],
            correct_option=1,
            explanation="Breadth-First Search (BFS) explores vertices level-by-level using a FIFO Queue.",
            time_limit_minutes=1
        ),
        AssessmentQuestion(
            id="camp_ds_05",
            type="mcq",
            modality="dsa_algorithms",
            section="data_structures",
            section_title=sec_ds,
            title="Binary Search Tree (BST): Inorder Traversal Property",
            prompt="What is the result of performing an Inorder (Left, Root, Right) traversal on a valid Binary Search Tree (BST)?",
            options=[
                "A) Elements listed in strictly decreasing order.",
                "B) Elements listed in strictly non-decreasing (sorted) order.",
                "C) Elements grouped by tree depth levels.",
                "D) Pre-order serialization of keys."
            ],
            correct_option=1,
            explanation="An inorder traversal of a BST visits all nodes in strictly non-decreasing sorted numerical order.",
            time_limit_minutes=1
        ),
        AssessmentQuestion(
            id="camp_ds_06",
            type="mcq",
            modality="dsa_algorithms",
            section="data_structures",
            section_title=sec_ds,
            title="Balanced Binary Trees: AVL Tree Rotations",
            prompt="What is the maximum permissible height difference (balance factor) between left and right subtrees in an AVL tree?",
            options=["A) 0", "B) 1", "C) 2", "D) log2(N)"],
            correct_option=1,
            explanation="An AVL tree strictly requires that the height difference (balance factor) between the left and right subtrees of every node is at most 1.",
            time_limit_minutes=1
        ),
        AssessmentQuestion(
            id="camp_ds_07",
            type="mcq",
            modality="dsa_algorithms",
            section="data_structures",
            section_title=sec_ds,
            title="Binary Heap: Min-Heap Extraction",
            prompt="In a standard binary Min-Heap of N elements, what is the time complexity to extract the minimum root element (`extract_min`)?",
            options=["A) O(1)", "B) O(log N)", "C) O(N)", "D) O(N log N)"],
            correct_option=1,
            explanation="While retrieving the minimum root is O(1), restoring the heap property (sift-down) takes O(log N) time.",
            time_limit_minutes=1
        ),
        AssessmentQuestion(
            id="camp_ds_08",
            type="mcq",
            modality="dsa_algorithms",
            section="data_structures",
            section_title=sec_ds,
            title="Hash Table: Collision Resolution Techniques",
            prompt="What is the difference between 'Chaining' and 'Open Addressing' in Hash Table collision resolution?",
            options=[
                "A) Chaining stores colliding elements in secondary linked lists/buckets; Open Addressing probes for alternative open slots within the table array.",
                "B) Open Addressing allocates infinite heap memory outside the hash table.",
                "C) Chaining guarantees zero collisions under any hash function.",
                "D) Open Addressing requires double hashing with O(N^2) space."
            ],
            correct_option=0,
            explanation="Separate chaining maintains external linked structures per bucket, whereas open addressing seeks vacant indices directly in the internal table.",
            time_limit_minutes=1
        ),
        AssessmentQuestion(
            id="camp_ds_09",
            type="mcq",
            modality="dsa_algorithms",
            section="data_structures",
            section_title=sec_ds,
            title="Sorting Stability: Definition & Algorithms",
            prompt="Which of the following sorting algorithms is guaranteed to be STABLE (preserves relative order of equal elements)?",
            options=["A) QuickSort", "B) MergeSort", "C) HeapSort", "D) Selection Sort"],
            correct_option=1,
            explanation="Standard MergeSort is stable because it does not exchange non-adjacent elements across equal comparison thresholds.",
            time_limit_minutes=1
        ),
        AssessmentQuestion(
            id="camp_ds_10",
            type="mcq",
            modality="dsa_algorithms",
            section="data_structures",
            section_title=sec_ds,
            title="Graph Representation: Sparse vs Dense Graphs",
            prompt="For a sparse graph with V vertices and E edges where E << V^2, which representation is significantly more space-efficient?",
            options=[
                "A) Adjacency Matrix (O(V^2))",
                "B) Adjacency List (O(V + E))",
                "C) Incidence Matrix (O(V * E^2))",
                "D) Complete Distance Matrix"
            ],
            correct_option=1,
            explanation="Adjacency List only stores active edges, taking O(V + E) space compared to O(V^2) for an Adjacency Matrix.",
            time_limit_minutes=1
        ),
        AssessmentQuestion(
            id="camp_ds_11",
            type="mcq",
            modality="dsa_algorithms",
            section="data_structures",
            section_title=sec_ds,
            title="Graph Algorithms: Directed Acyclic Graph (DAG) Order",
            prompt="Which algorithm produces a linear ordering of vertices in a Directed Acyclic Graph (DAG) such that for every directed edge u -> v, u comes before v?",
            options=[
                "A) Kruskal's Algorithm",
                "B) Topological Sort (Kahn's / DFS)",
                "C) Kosaraju's Algorithm",
                "D) Floyd-Warshall Algorithm"
            ],
            correct_option=1,
            explanation="Topological Sort orders vertices in a DAG respecting all dependency directions.",
            time_limit_minutes=1
        ),
        AssessmentQuestion(
            id="camp_ds_12",
            type="mcq",
            modality="dsa_algorithms",
            section="data_structures",
            section_title=sec_ds,
            title="Disjoint Set Union (DSU): Path Compression",
            prompt="With both Union by Rank and Path Compression optimizations, what is the amortized time complexity per operation in a Disjoint Set Union (Union-Find)?",
            options=[
                "A) O(1)",
                "B) O(α(N)) [Inverse Ackermann Function, practically O(1)]",
                "C) O(log N)",
                "D) O(N)"
            ],
            correct_option=1,
            explanation="Union by rank combined with path compression achieves nearly constant amortized time bounded by the Inverse Ackermann function α(N) < 5 for all practical inputs.",
            time_limit_minutes=1
        ),
        AssessmentQuestion(
            id="camp_ds_13",
            type="mcq",
            modality="dsa_algorithms",
            section="data_structures",
            section_title=sec_ds,
            title="Trie (Prefix Tree) Lookup Complexity",
            prompt="What is the time complexity to search for a word of length L in a Trie containing N total words?",
            options=["A) O(N * L)", "B) O(L)", "C) O(log N)", "D) O(N)"],
            correct_option=1,
            explanation="A Trie lookup checks each character along the path, requiring exactly O(L) time independent of the total number of words N in the tree.",
            time_limit_minutes=1
        ),
        AssessmentQuestion(
            id="camp_ds_14",
            type="mcq",
            modality="dsa_algorithms",
            section="data_structures",
            section_title=sec_ds,
            title="Two Pointers Technique: Sorted Array Two Sum",
            prompt="Given a sorted array of N numbers, finding if two numbers sum to target T using the two-pointer technique achieves what time and auxiliary space complexity?",
            options=[
                "A) O(N^2) Time, O(1) Space",
                "B) O(N log N) Time, O(N) Space",
                "C) O(N) Time, O(1) Auxiliary Space",
                "D) O(1) Time, O(N) Space"
            ],
            correct_option=2,
            explanation="Starting pointers at both ends and moving inward based on the comparison takes linear O(N) time with O(1) extra space.",
            time_limit_minutes=1
        ),
        AssessmentQuestion(
            id="camp_ds_15",
            type="mcq",
            modality="dsa_algorithms",
            section="data_structures",
            section_title=sec_ds,
            title="Shortest Path: Non-Negative Weighted Graphs",
            prompt="Which algorithm computes the single-source shortest path in a graph with non-negative edge weights in O((V + E) log V) time?",
            options=[
                "A) Bellman-Ford Algorithm",
                "B) Dijkstra's Algorithm with Min-Priority Queue",
                "C) Depth-First Search",
                "D) Floyd-Warshall Algorithm"
            ],
            correct_option=1,
            explanation="Dijkstra's algorithm using a min-heap priority queue efficiently finds shortest paths on graphs with non-negative weights in O((V + E) log V).",
            time_limit_minutes=1
        ),
        AssessmentQuestion(
            id="camp_ds_16",
            type="mcq",
            modality="dsa_algorithms",
            section="data_structures",
            section_title=sec_ds,
            title="Dynamic Programming: Memoization vs Tabulation",
            prompt="What is the distinction between 'Memoization' (top-down) and 'Tabulation' (bottom-up) in Dynamic Programming?",
            options=[
                "A) Memoization uses recursive call stacks and on-demand caching; Tabulation solves base subproblems iteratively in a table without recursion overhead.",
                "B) Memoization is O(2^N) while Tabulation is always O(1).",
                "C) Tabulation cannot solve optimal substructure problems.",
                "D) Memoization only applies to graphs while Tabulation applies to trees."
            ],
            correct_option=0,
            explanation="Top-down memoization stores recursive answers in a hash/array cache; bottom-up tabulation iteratively builds up subproblem answers starting from base cases.",
            time_limit_minutes=1
        ),
        AssessmentQuestion(
            id="camp_ds_17",
            type="mcq",
            modality="dsa_algorithms",
            section="data_structures",
            section_title=sec_ds,
            title="Binary Search Invariant",
            prompt="In a standard binary search over a sorted array, what must be updated when `target < arr[mid]`?",
            options=[
                "A) low = mid + 1",
                "B) high = mid - 1",
                "C) high = mid",
                "D) mid = mid / 2"
            ],
            correct_option=1,
            explanation="If the target is strictly less than the midpoint value, the search space shrinks to the left half by setting `high = mid - 1`.",
            time_limit_minutes=1
        ),
        AssessmentQuestion(
            id="camp_ds_18",
            type="mcq",
            modality="dsa_algorithms",
            section="data_structures",
            section_title=sec_ds,
            title="Circular Queue (Ring Buffer) Full Condition",
            prompt="In an array implementation of a Circular Queue with capacity C, what condition indicates that the queue is completely full (using `(front, rear)` pointers)?",
            options=[
                "A) front == rear",
                "B) (rear + 1) % C == front",
                "C) rear == C - 1",
                "D) front == -1"
            ],
            correct_option=1,
            explanation="The standard circular buffer full invariant is when advancing the rear pointer wraps around to match the front pointer: `(rear + 1) % C == front`.",
            time_limit_minutes=1
        )
    ])

    return questions


def build_campus_graduate_track() -> Dict[str, Any]:
    """Builds the complete Graduate / Campus Hire (Aptitude & Core CS) exam track."""
    questions = build_campus_graduate_questions()
    return {
        "track_id": "campus_graduate_engineer",
        "title": "Campus & Graduate Engineer (Aptitude & Core CS)",
        "badge": "Cognitive & CS Core",
        "description": "Standard 4-module evaluation for campus hires, graduates, and junior engineers: English Comprehension (12 Qs / 15m), Logical Ability (12 Qs / 15m), Quantitative Ability (14 Qs / 20m), and Data Structures (18 Qs / 20m). Total 56 questions in 70 minutes.",
        "skills": [
            "English Comprehension",
            "Logical Reasoning",
            "Quantitative Aptitude",
            "Data Structures & Algorithms"
        ],
        "duration_minutes": 70,
        "total_questions": len(questions),
        "sections": [
            "Section 1: English Comprehension (12 Questions · 15 Mins)",
            "Section 2: Logical Ability (12 Questions · 15 Mins)",
            "Section 3: Quantitative Ability (14 Questions · 20 Mins)",
            "Section 4: Data Structures (18 Questions · 20 Mins)"
        ],
        "section_breakdown": {
            "english": {"questions": 12, "minutes": 15, "label": "English Comprehension"},
            "logical": {"questions": 12, "minutes": 15, "label": "Logical Ability"},
            "quantitative": {"questions": 14, "minutes": 20, "label": "Quantitative Ability"},
            "data_structures": {"questions": 18, "minutes": 20, "label": "Data Structures"}
        },
        "questions": questions
    }

CAMPUS_GRADUATE_TRACK = build_campus_graduate_track()
