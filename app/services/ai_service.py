"""
AI Service – All OpenRouter API interactions for QuizGen.
Handles question generation, answer evaluation, performance analysis,
personalized recommendations, and AI tutoring.
"""

import json
import re
import os
import time
import requests
from datetime import datetime

from .question_bank import get_curated_mcq, get_curated_for_topic


# ─────────────────────────────────────────────────────────────
# Exam-specific prompt profiles — real exam data + current trends
# ─────────────────────────────────────────────────────────────

EXAM_PROFILES = {
    "JEE Main": {
        "subjects": ["Physics", "Chemistry", "Mathematics"],
        "style":    "NTA JEE Main official 2024 pattern",
        "total_questions": 90, "duration_minutes": 180,
        "marks_per_correct": 4, "negative_marks": 1,
        "difficulty_map": {
            "easy":   "JEE Main straightforward level — direct formula, NCERT concepts, single-step numericals",
            "medium": "JEE Main average level — multi-step numericals, application-based, moderate tricky options",
            "hard":   "JEE Main toughest 20% — multi-concept, close options, deep understanding required",
        },
        "instructions": (
            "Generate questions EXACTLY like NTA JEE Main 2023-2024 official papers. "
            "PHYSICS: Mechanics (vectors, kinematics, laws of motion, work-energy, rotational motion, SHM), "
            "Electrostatics (Coulomb's law, potential, capacitors), Magnetism (Biot-Savart, EMI, AC circuits), "
            "Modern Physics (photoelectric effect, nuclear reactions, semiconductors, logic gates), "
            "Waves & Optics (interference, diffraction, lenses, mirrors). "
            "Each Physics question MUST include numerical values, SI units, and require formula application. "
            "Bad example: 'What is Newton's first law?' — NEVER do this. "
            "Good example: 'A body of mass 4 kg is moving with velocity 3 m/s. A force of 8 N acts on it for 2 s. The final kinetic energy is:' "
            "CHEMISTRY: Organic (SN1/SN2, named reactions like Aldol/Cannizzaro/Friedel-Crafts, IUPAC nomenclature, isomerism), "
            "Physical Chemistry (Kp/Kc equilibrium, electrochemistry Nernst equation, thermodynamics ΔG/ΔH, solutions colligative properties), "
            "Inorganic (p-block groups 13-17, d-block properties, coordination compounds, periodic trends). "
            "MATHEMATICS: Integration (definite, by-parts, substitution), Differential equations, "
            "Complex numbers (argument, modulus, De Moivre), Matrices & Determinants, "
            "Conic Sections (parabola tangent/normal, ellipse, hyperbola), Probability (Bayes theorem, binomial distribution), "
            "3D Geometry (direction cosines, planes, lines). "
            "ALL options must be specific numerical values or chemical formulas — never 'All of the above' or vague text. "
            "Distribute: 33% Physics, 33% Chemistry, 33% Mathematics."
        ),
    },
    "JEE Advanced": {
        "subjects": ["Physics", "Chemistry", "Mathematics"],
        "style":    "IIT JEE Advanced Paper 1 & 2 pattern",
        "total_questions": 54, "duration_minutes": 180,
        "marks_per_correct": 4, "negative_marks": 2,
        "difficulty_map": {
            "easy":   "JEE Advanced foundational — still harder than JEE Main, requires solid concept understanding",
            "medium": "JEE Advanced standard — multi-concept problems, paragraph-based, requires analytical thinking",
            "hard":   "JEE Advanced toughest — IIT-level, counter-intuitive, multiple correct answers, integer type",
        },
        "instructions": (
            "Generate questions EXACTLY like IIT JEE Advanced official papers (2022-2024 pattern). "
            "Include MULTIPLE CORRECT MCQ questions (more than one option can be correct). "
            "Include INTEGER TYPE questions (exact numerical answer, no options, no negative marking). "
            "Include PARAGRAPH BASED questions (common passage with 2-3 questions). "
            "PHYSICS: Advanced mechanics (rotation + translation combined), Electromagnetism (complex circuits, non-uniform fields), "
            "Optics (wave optics problems, advanced ray optics), Modern Physics (nuclear decay chains, semiconductor devices), "
            "Thermodynamics (second law applications, Carnot cycle). "
            "CHEMISTRY: Multi-step organic synthesis, Complex equilibrium (simultaneous reactions, buffer), "
            "Electrochemistry (electrolysis calculations, cell EMF), Coordination chemistry (isomerism, Crystal Field Theory), "
            "Named reactions mechanism. "
            "MATHEMATICS: Advanced integration techniques, Differential equations (exact, linear, Bernoulli), "
            "Complex analysis, 3D geometry (complex planes/lines), Advanced probability, Sequences & series. "
            "Questions must require DEEP ANALYSIS not just formula recall. "
            "Options for multiple correct: mark ALL correct options. Ensure at least 2 options are correct sometimes."
        ),
    },
    "NEET": {
        "subjects": ["Physics", "Chemistry", "Biology (Botany)", "Biology (Zoology)"],
        "style":    "NTA NEET UG 2024 official pattern",
        "total_questions": 200, "duration_minutes": 200,
        "marks_per_correct": 4, "negative_marks": 1,
        "difficulty_map": {
            "easy":   "NEET straightforward — direct NCERT lines, basic concepts, factual recall",
            "medium": "NEET standard — NCERT application, diagram-based, moderate conceptual",
            "hard":   "NEET toughest — tricky NCERT exceptions, diagram interpretation, subtle factual",
        },
        "instructions": (
            "Generate questions EXACTLY like NTA NEET UG 2023-2024 official papers. "
            "BIOLOGY IS 50% WEIGHTAGE (most important): "
            "Botany: Cell biology (mitosis/meiosis stages, organelles), Genetics (Mendel's laws, linkage, mutations, DNA replication/repair), "
            "Plant Physiology (photosynthesis light/dark reactions Z-scheme, respiration glycolysis/Krebs cycle, plant hormones), "
            "Ecology (food chains, biogeochemical cycles, environmental issues), "
            "Reproduction in plants (types, embryology), Biotechnology (PCR, recombinant DNA, GMOs). "
            "Zoology: Human Physiology (digestion enzymes, circulation cardiac output, respiration volumes, excretion nephron, neural transmission, endocrine hormones), "
            "Animal Kingdom (chordates vs non-chordates, taxonomic features), "
            "Human Reproduction (gametogenesis, fertilization, embryonic development), "
            "Evolution (Darwinism, Hardy-Weinberg, population genetics), "
            "Human Health & Disease (immunity types, pathogens, cancer). "
            "PHYSICS (25%): NCERT-based with numericals — Laws of Motion, Work-Energy, Electrostatics, Current Electricity, Magnetism, Modern Physics. "
            "CHEMISTRY (25%): NCERT Organic (reactions, isomerism), Physical (solutions, equilibrium, thermodynamics), Inorganic (periodic trends, p-block). "
            "CRITICAL: Questions must be based on EXACT NCERT text/diagrams — NEET directly quotes from NCERT. "
            "Include questions with biological diagrams descriptions. "
            "Bad example: 'What is photosynthesis?' — too vague. "
            "Good example: 'Which of the following occurs in the stroma of chloroplast? (A) Light reactions (B) Calvin cycle (C) Photolysis of water (D) Cyclic photophosphorylation'"
        ),
    },
    "UPSC CSE": {
        "subjects": ["History", "Geography", "Polity", "Economy", "Environment", "Science & Technology", "Current Affairs"],
        "style":    "UPSC Civil Services Preliminary 2024 pattern",
        "total_questions": 180, "duration_minutes": 240,
        "marks_per_correct": 2, "negative_marks": 0.66,
        "difficulty_map": {
            "easy":   "UPSC direct factual — static GK, clear statements, straightforward current affairs",
            "medium": "UPSC standard — statement-based (2-3 statements, choose correct), match the column, moderate analysis",
            "hard":   "UPSC toughest — subtle distinctions, negative questions, 4-statement complex, current affairs depth",
        },
        "instructions": (
            "Generate questions EXACTLY like UPSC Civil Services Preliminary GS Paper 1 (2022-2024 papers). "
            "USE STATEMENT-BASED FORMAT: Most UPSC questions use format like: "
            "'Consider the following statements: 1. ... 2. ... 3. ... Which of the above is/are correct? (A) 1 only (B) 2 and 3 only (C) 1 and 3 only (D) 1, 2 and 3' "
            "HISTORY (20%): Ancient India (Indus Valley, Vedic period, Mauryan Empire, Gupta period), "
            "Medieval India (Delhi Sultanate, Mughal Empire, Bhakti/Sufi movements), "
            "Modern India (1857 revolt, Congress sessions, Gandhi's movements, Partition, Constitution making). "
            "GEOGRAPHY (15%): Indian geography (rivers, soils, climate, agriculture), World geography (ocean currents, climate zones, minerals). "
            "POLITY (20%): Constitutional provisions (Articles, Amendments, Schedules), Parliament, Judiciary, Governor, Constitutional bodies. "
            "ECONOMY (15%): GDP, inflation, budget, RBI policies, banking, trade, WTO, recent economic schemes. "
            "ENVIRONMENT (15%): Biodiversity hotspots, Ramsar sites, wildlife sanctuaries, climate change, environmental laws, recent environmental news. "
            "SCIENCE & TECHNOLOGY (10%): Recent space missions (ISRO, NASA), biotech developments, AI/digital policy, recent scientific discoveries. "
            "CURRENT AFFAIRS (5%): Events from last 12 months — international summits, awards, government schemes launched in 2023-2024. "
            "CRITICAL: Questions must test NUANCED understanding, not simple recall. "
            "Include NEGATIVE questions: 'Which of the following is NOT correct about...?' "
            "Include MATCH THE COLUMN: 'Match List I with List II...'"
        ),
    },
    "CAT": {
        "subjects": ["Verbal Ability & Reading Comprehension", "Data Interpretation & Logical Reasoning", "Quantitative Aptitude"],
        "style":    "IIM CAT 2024 official pattern",
        "total_questions": 66, "duration_minutes": 120,
        "marks_per_correct": 3, "negative_marks": 1,
        "difficulty_map": {
            "easy":   "CAT easy — straightforward RC, simple DI tables, direct QA formulas",
            "medium": "CAT standard — inference-based RC, complex DI sets, 2-step QA",
            "hard":   "CAT toughest — abstract VARC, multi-variable DI, advanced QA (number theory, geometry)",
        },
        "instructions": (
            "Generate questions EXACTLY like IIM CAT 2023-2024 official papers. "
            "VARC (36%): "
            "RC Passages (500-700 words on economics/philosophy/science) with 3-4 inference questions: "
            "Types: 'What is the author's primary argument?', 'Which statement would weaken the author's claim?', 'What can be inferred from paragraph 3?' "
            "Para-Jumble: 5 sentences ABCDE, find correct order. "
            "Para Summary: Choose the best one-line summary of a paragraph. "
            "Odd Sentence Out: 4 sentences, find the one that doesn't fit. "
            "DILR (30%): "
            "Data Sets (4-6 questions per set): Bar charts, Line graphs, Tables, Venn diagrams, Scheduling problems, Network problems. "
            "Example: 'Six people — A, B, C, D, E, F — are seated in a row. A is not adjacent to B. D sits at one of the ends...' "
            "QA (33%): "
            "Number Theory (HCF/LCM, divisibility, remainders, factors), "
            "Arithmetic (percentages, profit-loss, time-work, mixtures, simple/compound interest), "
            "Algebra (quadratics, logarithms, inequalities, functions), "
            "Geometry (triangles, circles, trigonometry, coordinate geometry), "
            "Modern Math (set theory, permutations, probability). "
            "CAT rewards elegant shortcuts — include questions that have quick mental math solutions. "
            "TITA questions (Type In The Answer): Some QA questions have no options — provide these too."
        ),
    },
    "GATE": {
        "subjects": ["General Aptitude", "Engineering Mathematics", "Technical Core (CS/EC/EE/ME)"],
        "style":    "GATE 2024 official pattern",
        "total_questions": 65, "duration_minutes": 180,
        "marks_per_correct": 2, "negative_marks": 0.66,
        "difficulty_map": {
            "easy":   "GATE 1-mark questions — direct formula, basic concepts, straightforward definitions",
            "medium": "GATE 2-mark questions — application, multi-step, moderate analysis",
            "hard":   "GATE toughest 2-mark — complex analysis, tricky edge cases, requires deep subject mastery",
        },
        "instructions": (
            "Generate questions EXACTLY like GATE 2023-2024 official papers. "
            "Include both MCQ and NAT (Numerical Answer Type) questions. "
            "GENERAL APTITUDE (15 marks): "
            "Verbal: Sentence completion, Reading comprehension, Critical reasoning, Word analogies. "
            "Numerical: Number series, Data interpretation, Mensuration, Speed-distance-time. "
            "ENGINEERING MATHEMATICS (13 marks): "
            "Linear Algebra (eigenvalues, rank, system of equations), "
            "Calculus (partial derivatives, multiple integrals, gradient/curl/divergence), "
            "Probability & Statistics (Bayes theorem, distributions, expected value), "
            "Differential Equations (ODE types, Laplace transform), "
            "Discrete Mathematics (graph theory, boolean algebra, relations). "
            "TECHNICAL SUBJECTS (CS branch, 72 marks): "
            "Data Structures & Algorithms (time complexity, sorting, trees, graphs, dynamic programming), "
            "Operating Systems (process scheduling, memory management, deadlock, file systems), "
            "Database Management (SQL queries, normalization, transaction, ER diagrams), "
            "Computer Networks (OSI layers, TCP/IP, routing, congestion control), "
            "Theory of Computation (DFA/NFA, context-free grammars, Turing machines, decidability), "
            "Computer Organization (pipelining, cache, instruction formats). "
            "NAT questions must have a specific single numerical answer (e.g., '3', '0.75', '12'). "
            "Mark NAT questions by setting options to [] and correctAnswer to the numerical value as string."
        ),
    },
    "SSC CGL": {
        "subjects": ["General Intelligence & Reasoning", "General Awareness", "Quantitative Aptitude", "English Language"],
        "style":    "SSC CGL Tier 1 2024 pattern",
        "total_questions": 100, "duration_minutes": 60,
        "marks_per_correct": 2, "negative_marks": 0.5,
        "difficulty_map": {
            "easy":   "SSC CGL easy — direct reasoning, basic static GK, simple arithmetic",
            "medium": "SSC CGL standard — new pattern puzzles, current GK, 2-step maths",
            "hard":   "SSC CGL tough — complex seating arrangements, tricky GK, advanced maths DI",
        },
        "instructions": (
            "Generate questions EXACTLY like SSC CGL Tier 1 2023-2024 official papers. "
            "REASONING (25 Qs): "
            "Analogies (word, number, letter), Classification, Series (number, letter, mixed), "
            "Coding-Decoding (new pattern — table-based), Blood Relations, "
            "Direction Sense, Seating Arrangement, Syllogism, Matrix-based puzzles, "
            "Mirror/Water images, Paper folding/cutting, Embedded figures. "
            "GENERAL AWARENESS (25 Qs): "
            "History (freedom movement, Mughal/Maurya, culture, art), "
            "Geography (rivers, mountains, dams, states capitals, national parks), "
            "Polity (Constitution, Articles, Amendments, Government bodies), "
            "Economy (Budget 2024 highlights, economic terms, government schemes like PM-Kisan, PM-Awas), "
            "Science (physics/chemistry/biology basics, inventions, diseases), "
            "Current Affairs (last 6 months: sports, awards, summits, recent PM/CM appointments). "
            "QUANTITATIVE APTITUDE (25 Qs): "
            "Percentage, Profit-Loss, Discount, Simple & Compound Interest, "
            "Ratio & Proportion, Time-Work, Time-Speed-Distance, Pipes & Cisterns, "
            "Data Interpretation (bar graph, pie chart, table — 5 questions per set), "
            "Geometry (triangles, circles, area/volume), Trigonometry (basic identities, heights & distances), "
            "Number System (HCF/LCM, divisibility, surds). "
            "ENGLISH (25 Qs): "
            "Reading Comprehension (1 passage, 5 questions), "
            "Fill in the Blanks (articles, prepositions, tense), Error Spotting, "
            "Sentence Improvement, Active/Passive, Direct/Indirect Speech, "
            "Synonyms, Antonyms, One Word Substitution, Idioms & Phrases, Spelling Correction. "
            "SPEED IS KEY: Questions should be solvable in 30-40 seconds. "
            "Marks: +2 correct, -0.5 wrong."
        ),
    },
    "IBPS PO": {
        "subjects": ["Reasoning Ability", "English Language", "Quantitative Aptitude"],
        "style":    "IBPS PO Prelims 2024 pattern",
        "total_questions": 100, "duration_minutes": 60,
        "marks_per_correct": 1, "negative_marks": 0.25,
        "difficulty_map": {
            "easy":   "IBPS straightforward — simple puzzles, basic DI, direct grammar",
            "medium": "IBPS standard — complex puzzles, caselet DI, inference RC",
            "hard":   "IBPS tough — multi-variable puzzles, complex DI, tricky English",
        },
        "instructions": (
            "Generate questions EXACTLY like IBPS PO Prelims 2023-2024 pattern. "
            "REASONING (35 Qs — most important): "
            "Puzzles & Seating Arrangement (HIGH PRIORITY, 20+ questions): "
            "Linear arrangement (8 people, some face north/south), "
            "Circular arrangement (8 people facing centre/outside), "
            "Floor puzzle (8 floors, multiple variables), "
            "Box/Month/Day puzzle. "
            "Syllogisms (all/some/no statements, follow-up conclusions), "
            "Inequalities (A>B≥C<D, find relationship between A and D), "
            "Blood Relations (family tree based), "
            "Direction & Distance (person walks North 5km then East 3km...), "
            "Coding-Decoding (if BANK is coded as ECPN, then LOAN is coded as?). "
            "ENGLISH (30 Qs): "
            "Reading Comprehension (passage + 5-7 questions on main idea, inference, vocabulary), "
            "Cloze Test (fill 5 blanks in a paragraph), "
            "Error Spotting (4 parts of sentence, find grammatical error), "
            "Sentence Rearrangement (ABCDE → find correct order), "
            "Fill in the Blanks (choose appropriate word from options). "
            "QUANTITATIVE (35 Qs): "
            "Data Interpretation (3 DI sets × 5 questions each): "
            "Table DI (sales/profit data), Bar graph, Pie chart + table combination. "
            "Number Series (find missing term: 2, 6, 12, 20, 30, ?), "
            "Quadratic Equations (x²-5x+6=0, y²-7y+12=0, compare x and y), "
            "Approximation (find approximate value of 23.98² + 47.03×√81), "
            "Arithmetic (percentage, profit-loss, SI/CI, time-work). "
            "Marks: +1 correct, -0.25 wrong. Sectional time limit: 20 min each."
        ),
    },
    "SAT": {
        "subjects": ["Reading & Writing", "Mathematics"],
        "style":    "Digital SAT 2024 adaptive pattern",
        "total_questions": 98, "duration_minutes": 134,
        "marks_per_correct": 1, "negative_marks": 0,
        "difficulty_map": {
            "easy":   "SAT Module 1 level — direct vocabulary, clear inference, basic algebra",
            "medium": "SAT standard — context vocabulary, moderate inference, algebra II",
            "hard":   "SAT Module 2 hard — complex inference, advanced math (statistics, geometry, quadratics)",
        },
        "instructions": (
            "Generate questions EXACTLY like Digital SAT 2024 official papers. "
            "READING & WRITING (54 Qs, 64 min): "
            "Craft & Structure: Words in Context (vocabulary based on passage context, NOT memorization), "
            "Text Structure & Purpose (why does author include this detail?), "
            "Cross-Text Connections (how do two passages relate?). "
            "Information & Ideas: Central Ideas & Details, Command of Evidence (textual + quantitative), "
            "Inferences (what can be inferred based on the passage?). "
            "Standard English Conventions: Boundaries (run-ons, fragments, semicolons), "
            "Form/Structure/Sense (subject-verb agreement, pronoun, modifier, verb tense). "
            "MATHEMATICS (44 Qs, 70 min): "
            "Algebra: Linear equations, Systems of equations, Linear inequalities, "
            "Linear functions (slope, y-intercept, graphing). "
            "Advanced Math: Quadratic equations (factoring, quadratic formula), "
            "Polynomial functions, Exponential functions, Rational expressions. "
            "Problem Solving & Data Analysis: Ratios, rates, proportions, percentages, "
            "Statistics (mean, median, spread, normal distribution), "
            "Probability, Data from graphs/tables. "
            "Geometry & Trigonometry: Area, volume, angle relationships, "
            "Right triangle trigonometry (sin/cos/tan), Circle equations. "
            "No negative marking. Both student-produced response (grid-in) and MCQ formats."
        ),
    },
    "GRE": {
        "subjects": ["Verbal Reasoning", "Quantitative Reasoning"],
        "style":    "New shorter GRE 2024 pattern (ETS)",
        "total_questions": 54, "duration_minutes": 118,
        "marks_per_correct": 1, "negative_marks": 0,
        "difficulty_map": {
            "easy":   "GRE Section 1 — moderate vocabulary, clear passages, straightforward quant",
            "medium": "GRE standard — advanced vocabulary (esoteric, laconic, recondite), inference passages, multi-step quant",
            "hard":   "GRE Section 2 hard (after strong Section 1) — most difficult text completion, hard inference, complex quant",
        },
        "instructions": (
            "Generate questions EXACTLY like new ETS GRE General Test 2024 (shorter format). "
            "VERBAL REASONING (27 Qs): "
            "Text Completion (1, 2, or 3 blanks): "
            "1 blank: 'The scientist's ________ approach to the problem impressed her colleagues. (A) perfunctory (B) methodical (C) capricious (D) obdurate (E) ephemeral' "
            "2 blanks: 'The author's prose was (i)________, yet her arguments were (ii)________.' "
            "3 blanks: Full paragraph with 3 blanks, each with 3 options. "
            "Sentence Equivalence (find TWO words that complete sentence and give same meaning): "
            "'The politician's speech was so ________ that even his opponents were moved. [6 options — pick 2]' "
            "Reading Comprehension: Short (1-2 paragraphs, 1-3 questions) and Long (4-5 paragraphs, 3-6 questions) passages. "
            "Question types: Main Idea, Author's Purpose, Inference, Strengthen/Weaken argument, Vocabulary in context. "
            "Use ADVANCED GRE vocabulary: abscond, equivocate, solipsistic, peripatetic, laconic, sanguine, obsequious, truculent, enervate, garrulous. "
            "QUANTITATIVE REASONING (27 Qs): "
            "Quantitative Comparison: 'Column A vs Column B — which is greater?' (4 options: A greater, B greater, equal, cannot determine) "
            "Problem Solving MCQ and Numeric Entry. "
            "Topics: Arithmetic (fractions, decimals, percentages, number properties), "
            "Algebra (equations, inequalities, functions, coordinate geometry), "
            "Geometry (lines, triangles, circles, 3D shapes), "
            "Data Analysis (statistics, probability, distributions, data interpretation). "
            "Score range 130-170 per section. No negative marking."
        ),
    },
    "GMAT": {
        "subjects": ["Verbal", "Quantitative", "Data Insights"],
        "style":    "GMAT Focus Edition 2024",
        "total_questions": 64, "duration_minutes": 135,
        "marks_per_correct": 1, "negative_marks": 0,
        "difficulty_map": {
            "easy":   "GMAT easy — clear CR arguments, basic quant, straightforward DS",
            "medium": "GMAT standard — subtle CR assumptions, 2-step quant, moderate DS",
            "hard":   "GMAT tough — complex CR, advanced quant, multi-condition DS",
        },
        "instructions": (
            "Generate questions EXACTLY like GMAT Focus Edition 2024. "
            "VERBAL (23 Qs): "
            "Critical Reasoning (most important — 60% of Verbal): "
            "Strengthen: 'Which answer choice, if true, most strengthens the argument?' "
            "Weaken: 'Which answer choice, if true, most undermines the conclusion?' "
            "Assumption: 'The argument depends on which assumption?' "
            "Flaw: 'The argument is flawed because it...' "
            "Inference: 'If the statements are true, which must also be true?' "
            "Bold-faced: 'The two bold-faced portions play what roles in the argument?' "
            "Reading Comprehension (40% of Verbal): 3-4 passages (200-350 words each), business/science topics. "
            "Question types: Main Idea, Supporting Idea, Inference, Application, Logical Structure. "
            "QUANTITATIVE (21 Qs — no geometry): "
            "Problem Solving: Standard word problems — percentage, ratio, work, speed, profit. "
            "Arithmetic: Number properties (factors, multiples, primes, remainders), "
            "Algebra: Equations (linear, quadratic), functions, absolute value, inequalities. "
            "Statistics: Mean, median, range, standard deviation. "
            "DATA INSIGHTS (20 Qs — new section): "
            "Data Sufficiency: 'Is the data in (1) alone sufficient? In (2) alone? Together?' "
            "Choices: (A) 1 alone, (B) 2 alone, (C) together, (D) either alone, (E) neither together "
            "Multi-Source Reasoning: Multiple tabs/sources, answer questions from combined data. "
            "Table Analysis: Sortable table, True/False or Yes/No questions. "
            "Graphics Interpretation: Chart with fill-in-the-blank statements. "
            "Score range 205-805. Computer-adaptive per section."
        ),
    },
    "MCAT": {
        "subjects": ["Biology/Biochemistry", "Chemistry/Physics", "Psychology/Sociology", "Critical Analysis"],
        "style":    "AAMC MCAT 2024 passage-based pattern",
        "total_questions": 230, "duration_minutes": 375,
        "marks_per_correct": 1, "negative_marks": 0,
        "difficulty_map": {
            "easy":   "MCAT foundational — direct passage information, basic science concepts",
            "medium": "MCAT standard — inference from passage, application to new scenario",
            "hard":   "MCAT toughest — complex data interpretation, multi-concept integration, experimental design",
        },
        "instructions": (
            "Generate questions EXACTLY like AAMC MCAT 2024 official passage-based format. "
            "ALL questions must be tied to a short passage (3-5 sentences scientific scenario). "
            "Format: Provide a mini-passage first, then 1-2 questions based on it. "
            "BIOLOGICAL & BIOCHEMICAL FOUNDATIONS (59 Qs): "
            "Biochemistry: Enzyme kinetics (Michaelis-Menten, inhibition types), Metabolism (glycolysis, TCA cycle, oxidative phosphorylation, fatty acid oxidation), "
            "DNA replication/transcription/translation (mutations, gene regulation), Protein structure (primary to quaternary, denaturation). "
            "Biology: Cell division (mitosis/meiosis checkpoints), Signal transduction (GPCR, receptor tyrosine kinase), "
            "Nervous system (action potential, synaptic transmission, neurotransmitters), "
            "Endocrine system (hormone mechanisms, feedback loops), Immune system (innate vs adaptive, antibodies, complement). "
            "CHEMICAL & PHYSICAL FOUNDATIONS (59 Qs): "
            "General Chemistry: Electrochemistry (galvanic cells, Nernst equation), Acid-Base (Henderson-Hasselbalch, buffers, titration curves), "
            "Thermodynamics (ΔG, Keq, Le Chatelier), Kinetics (rate laws, activation energy). "
            "Organic Chemistry: Stereochemistry (R/S, E/Z, Fischer projections), Reaction mechanisms (nucleophilic addition, substitution, elimination), "
            "Spectroscopy (NMR, IR, MS interpretation), Amino acid chemistry. "
            "Physics: Fluid mechanics (Bernoulli, pressure), Optics (lenses, mirrors), Electricity (circuits, capacitors). "
            "PSYCHOLOGICAL, SOCIAL, BIOLOGICAL FOUNDATIONS (59 Qs): "
            "Psychology: Sensation & Perception, Learning & Memory (classical/operant conditioning, memory types), "
            "Cognition, Development (Piaget, Erikson stages), Personality theories, Social psychology (Milgram, Stanford Prison), "
            "Psychological disorders (DSM criteria). "
            "Sociology: Social stratification, Culture, Health disparities, Social institutions. "
            "Research methods: Experimental design, Statistics (Type I/II errors, p-value, confidence intervals). "
            "CARS (53 Qs): Humanities/social science passages, inference and reasoning only (no science knowledge needed). "
            "Score 472-528. No negative marking."
        ),
    },
    "RRB NTPC": {
        "subjects": ["Mathematics", "General Intelligence & Reasoning", "General Awareness"],
        "style":    "RRB NTPC CBT 1 2024 pattern",
        "total_questions": 100, "duration_minutes": 90,
        "marks_per_correct": 1, "negative_marks": 0.33,
        "difficulty_map": {
            "easy":   "RRB NTPC easy — basic maths, simple reasoning, static GK",
            "medium": "RRB NTPC standard — moderate maths, mixed reasoning, current affairs",
            "hard":   "RRB NTPC tough — DI sets, complex reasoning, specific Railway GK",
        },
        "instructions": (
            "Generate questions EXACTLY like RRB NTPC CBT 1 2023-2024 pattern. "
            "MATHEMATICS (30 Qs): "
            "Number System (HCF, LCM, factors, primes), Decimals & Fractions, "
            "Percentage (direct, reverse, successive), Profit-Loss-Discount, "
            "Simple Interest & Compound Interest (half-yearly, quarterly), "
            "Ratio & Proportion (direct, inverse, compound), "
            "Time & Work (pipes & cisterns, efficiency based), "
            "Speed-Distance-Time (trains, boats & streams, relative motion), "
            "Mensuration (area of triangles/circles/quadrilaterals, volume of cylinders/cones/spheres), "
            "Trigonometry (basic ratios, heights & distances), "
            "Statistics (mean, median, mode, range), "
            "Data Interpretation (table, bar graph). "
            "REASONING (30 Qs): "
            "Analogies, Classification, Number/Letter Series, "
            "Coding-Decoding, Blood Relations, Direction Sense, "
            "Venn Diagrams, Syllogisms, Mathematical Operations, "
            "Mirror Images, Cubes & Dice, Seating Arrangement (simple). "
            "GENERAL AWARENESS (40 Qs — highest weightage): "
            "Indian Railways (history, zones, types of trains, recent Railway Budget 2024, Railway schemes), "
            "Indian History (ancient, medieval, modern freedom struggle), "
            "Indian Geography (major rivers, mountain ranges, states), "
            "Indian Polity (Constitution basics, Parliament, Article 370 changes), "
            "Economy (recent govt schemes, GDP, budget terms), "
            "Science & Technology (recent ISRO missions, important inventions), "
            "Sports (recent cricket World Cup, Olympics, Asian Games results 2023-2024), "
            "Current Affairs (last 6-12 months: important appointments, awards, summits). "
            "Marks: +1 correct, -1/3 wrong."
        ),
    },
    "DEFAULT": {
        "subjects": ["General Knowledge", "Reasoning", "Aptitude"],
        "style":    "competitive exam standard",
        "total_questions": 100, "duration_minutes": 60,
        "marks_per_correct": 1, "negative_marks": 0,
        "difficulty_map": {
            "easy":   "basic level — direct questions, factual recall, simple reasoning",
            "medium": "standard level — application-based, moderate analysis",
            "hard":   "advanced level — complex multi-step, deep analysis required",
        },
        "instructions": (
            "Generate high-quality competitive exam questions. "
            "Mix analytical, factual, and application-based questions. "
            "All 4 options must be plausible — avoid obviously wrong options. "
            "Include questions from multiple cognitive levels: recall, understanding, application, analysis."
        ),
    },
}

def _get_exam_profile(exam_name: str) -> dict:
    """Return the exam profile, with fuzzy matching for partial names."""
    if not exam_name:
        return EXAM_PROFILES["DEFAULT"]

    # Exact match
    if exam_name in EXAM_PROFILES:
        return EXAM_PROFILES[exam_name]

    # Fuzzy match (case-insensitive, partial)
    name_lower = exam_name.lower()
    for key in EXAM_PROFILES:
        if key.lower() in name_lower or name_lower in key.lower():
            return EXAM_PROFILES[key]

    return EXAM_PROFILES["DEFAULT"]


# ─────────────────────────────────────────────────────────────
# Config helpers
# ─────────────────────────────────────────────────────────────

def _openrouter_api_key() -> str:
    return os.getenv("OPENROUTER_API_KEY", "").strip()


def _openrouter_model() -> str:
    return (os.getenv("OPENROUTER_MODEL") or "openrouter/free").strip()


# ─────────────────────────────────────────────────────────────
# Error classification
# ─────────────────────────────────────────────────────────────

def _is_auth_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return "401" in msg or "unauthorized" in msg or "invalid api key" in msg


def _is_quota_error(exc: Exception) -> bool:
    if _is_auth_error(exc):
        return False
    msg = str(exc).lower()
    return (
        "429" in msg or "quota" in msg or "exceeded" in msg
        or "rate_limit" in msg or "too many requests" in msg
    )


def _ai_unavailable_msg(exc: Exception, feature: str = "AI") -> str:
    if _is_auth_error(exc):
        return f"The {feature} service is unavailable due to an invalid API key."
    if _is_quota_error(exc):
        return f"The {feature} service has hit its rate limit. Please try again shortly."
    return f"The {feature} service is temporarily unavailable. Please try again."


# ─────────────────────────────────────────────────────────────
# Core API call
#
# FIX: previously this hardcoded list ignored OPENROUTER_MODEL from
# .env entirely, and contained stale/unavailable free model IDs
# (openchat/openchat-3.5:free does not exist on OpenRouter).
# Now: your .env model is tried FIRST, then these current (June 2026)
# free models as fallback. Update this list any time from
# https://openrouter.ai/models?order=top-weekly&max_price=0
# ─────────────────────────────────────────────────────────────

FALLBACK_MODELS = [
    "meta-llama/llama-4-maverick:free",
    "deepseek/deepseek-chat-v3-0324:free",
    "openrouter/free",   # auto-router across whatever free models are live
]


def _call(prompt: str) -> str:
    api_key = _openrouter_api_key()
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is not set.")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": os.getenv("FRONTEND_URL", "http://localhost:3000"),
        "X-Title": "QuizGen",
    }

    payload_template = {
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a JSON API, not a chat assistant. "
                    "Respond with ONLY a valid JSON array — no markdown, no LaTeX, "
                    "no <think> tags, no reasoning, no explanation, no commentary "
                    "before or after the array. The first character of your reply "
                    "must be '[' and the last character must be ']'."
                )
            },
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.5,
        # FIX: 2048 was too small once a model spends tokens "thinking" —
        # the JSON either got cut off mid-array or never appeared at all.
        "max_tokens": 4096,
        # FIX: for hybrid reasoning models (DeepSeek-R1 style, Nemotron, etc.)
        # this keeps the chain-of-thought out of the returned `content` field
        # entirely, so we don't have to parse JSON out of "We need to output...".
        "reasoning": {"exclude": True},
    }

    # FIX: try the model configured in .env first, then fall back.
    configured_model = _openrouter_model()
    models_to_try = [configured_model] + [
        m for m in FALLBACK_MODELS if m != configured_model
    ]

    last_err = None

    for model in models_to_try:
        try:
            print(f"[AI] Trying model: {model}")

            payload = {**payload_template, "model": model}

            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=60,
            )

            if response.status_code == 401:
                raise RuntimeError("401 invalid API key")

            if response.status_code == 402:
                raise RuntimeError("402 insufficient credits")

            if response.status_code == 429:
                raise RuntimeError("429 rate limit")

            if not response.ok:
                raise RuntimeError(f"{response.status_code}: {response.text}")

            data = response.json()
            text = data["choices"][0]["message"]["content"]

            if isinstance(text, list):
                text = "".join(text)

            if text:
                print(f"[AI] Success using {model}")
                return text.strip()

        except Exception as e:
            print(f"[AI] Failed model {model}: {e}")
            last_err = e
            # FIX: an invalid API key will never succeed on any model — stop immediately.
            if _is_auth_error(e):
                raise RuntimeError("401 invalid API key") from e
            continue

    # ALL FAILED
    raise RuntimeError(f"All models failed: {last_err}")


# ─────────────────────────────────────────────────────────────
# Robust JSON extraction (bracket-depth counting)
# ─────────────────────────────────────────────────────────────

def _extract_json_array(text: str) -> str:
    start = text.find('[')
    if start == -1:
        raise ValueError("No JSON array found in AI response")
    depth, in_string, escape_next = 0, False, False
    for i in range(start, len(text)):
        ch = text[i]
        if escape_next:             escape_next = False; continue
        if ch == '\\' and in_string: escape_next = True; continue
        if ch == '"':               in_string = not in_string; continue
        if in_string:               continue
        if ch == '[':               depth += 1
        elif ch == ']':
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    raise ValueError("Incomplete JSON array in AI response")


def _clean_raw(raw: str) -> str:
    if not isinstance(raw, str):
        return json.dumps(raw)
    clean = raw.strip()
    clean = re.sub(r"```(?:json)?\s*", "", clean)
    clean = clean.replace("```", "").strip()

    # Strip any preamble text before the JSON actually starts.
    # FIX (major): the old version checked "[" then "{" as two separate
    # loop iterations. For a clean response like '[{"id":...}]', it found
    # "[" at index 0 (no-op, since the condition required idx > 0), then
    # fell through to check "{" — which sits at index 1 — and "stripped"
    # everything before it, i.e. it deleted the legitimate opening "[".
    # That silently turned a perfectly valid question array into a bare
    # object, which is why even successful AI calls were producing
    # "Generated 0 questions": _extract_json_array then grabbed the first
    # *nested* array it could find (an "options" list), json.loads'd that
    # into a list of plain strings, and _sanitize_questions correctly
    # discarded all of them for not being dicts.
    bracket_positions = [i for i in (clean.find("["), clean.find("{")) if i != -1]
    if bracket_positions:
        start = min(bracket_positions)
        if start > 0 and clean[:start].strip():
            clean = clean[start:]

    # Convert Python repr to JSON if needed
    if clean.startswith("[") and "'" in clean[:30] and '"' not in clean[:30]:
        clean = _python_repr_to_json(clean)
    return clean


def _python_repr_to_json(text: str) -> str:
    """Convert Python repr (single quotes) to valid JSON."""
    import ast
    try:
        obj = ast.literal_eval(text.strip())
        return json.dumps(obj)
    except Exception:
        return text


def _parse_json(raw: str) -> dict | list:
    if not raw or not str(raw).strip():
        raise ValueError("Empty model response")
    clean = _clean_raw(str(raw))
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        pass
    for open_ch, close_ch in [("[", "]"), ("{", "}")]:
        start = clean.find(open_ch)
        if start == -1:
            continue
        depth, in_string, escape_next = 0, False, False
        for i in range(start, len(clean)):
            ch = clean[i]
            if escape_next:               escape_next = False; continue
            if ch == '\\' and in_string:  escape_next = True;  continue
            if ch == '"':                 in_string = not in_string; continue
            if in_string:                 continue
            if ch == open_ch:             depth += 1
            elif ch == close_ch:
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(clean[start:i + 1])
                    except json.JSONDecodeError:
                        break
    raise ValueError("Could not parse JSON from model output")


# ─────────────────────────────────────────────────────────────
# Question normalization
# ─────────────────────────────────────────────────────────────

def _sanitize_questions(questions: list, topic: str, q_type: str) -> list[dict]:
    """
    Normalize fields so both 'text' and 'question_text' always exist,
    preventing frontend field-name mismatches.
    """
    out = []
    for i, q in enumerate(questions):
        if not isinstance(q, dict):
            continue

        # Normalize text fields
        raw_text = q.get("text") or q.get("question_text") or q.get("question") or ""
        q["text"]          = raw_text
        q["question_text"] = raw_text

        q.setdefault("id",          f"q_{i}_{datetime.utcnow().timestamp():.0f}")
        q.setdefault("marks",       1)
        q.setdefault("explanation", "")
        q.setdefault("topic",       topic)
        q.setdefault("difficulty",  "medium")

        if q_type in ("mcq", "MCQ"):
            if not isinstance(q.get("options"), list) or len(q["options"]) < 2:
                q["options"] = ["Option A", "Option B", "Option C", "Option D"]
            ca = q.get("correctAnswer", 0)
            if not isinstance(ca, int) or ca >= len(q["options"]):
                q["correctAnswer"] = 0
        else:
            q.setdefault("options",        [])
            q.setdefault("correctAnswer",  None)

        out.append(q)
    return out


# ─────────────────────────────────────────────────────────────
# 1. Core question generator (used by other functions)
# ─────────────────────────────────────────────────────────────

def generate_questions(
    topic: str,
    q_type: str = "mcq",
    difficulty: str = "medium",
    count: int = 10,
    extra_instructions: str = "",
) -> list[dict]:
    prompt = f"""
You are a professional exam paper setter.

Generate {count} high-quality {q_type.upper()} questions about: {topic}
Difficulty: {difficulty}
{extra_instructions}

Return ONLY valid JSON array, no markdown, no extra text:
[
  {{
    "id": "unique-string",
    "type": "{q_type}",
    "text": "Full question text",
    "options": ["Option A", "Option B", "Option C", "Option D"],
    "correctAnswer": 0,
    "explanation": "Why correct answer is correct",
    "topic": "Sub-topic name",
    "difficulty": "{difficulty}",
    "marks": 1
  }}
]
"""
    try:
        raw = _call(prompt)
        questions = _parse_json(raw)
        if not isinstance(questions, list):
            raise ValueError("Expected list")
        return _sanitize_questions(questions, topic, q_type)
    except Exception as e:
        print(f"[AI] generate_questions failed: {e}")
        if q_type not in ("mcq", "MCQ"):
            return []
        return get_curated_for_topic(topic, difficulty, count)


# ─────────────────────────────────────────────────────────────
# 2. Exam-specific question generation
# ─────────────────────────────────────────────────────────────

def generate_questions_for_exam(
    exam: dict,
    country_name: str = "",
    q_type: str = "mcq",
    difficulty: str = "medium",
    count: int = 10,
) -> dict:
    """
    Generate real exam-level questions using detailed exam-specific profiles.
    Difficulty is passed directly to prompt — never overridden.
    """
    name = (exam or {}).get("name") or "Practice Exam"
    desc = (exam or {}).get("description") or ""

    # Cap at 10 to avoid JSON truncation on small free models
    safe_count = min(count, 10)

    # Get exam-specific profile (with difficulty_map)
    profile           = _get_exam_profile(name)
    exam_instructions = profile["instructions"]
    subjects_hint     = ", ".join(profile["subjects"])
    style_hint        = profile["style"]
    marks_per_q       = profile.get("marks_per_correct", 4)
    neg_marks         = profile.get("negative_marks", 1)
    real_total_q      = profile.get("total_questions", 100)
    real_duration     = profile.get("duration_minutes", 60)

    # Use exam-specific difficulty description from profile
    difficulty_map     = profile.get("difficulty_map", {})
    difficulty_context = difficulty_map.get(
        difficulty.lower(),
        f"{difficulty} level questions matching {name} standard"
    )

    # Time per question in real exam
    secs_per_q = round((real_duration * 60) / real_total_q)

    # Q type specific instruction
    qtype_instruction = {
        "mcq":         "All questions must be single-correct MCQ with exactly 4 options (A/B/C/D). correctAnswer is 0-based index.",
        "descriptive": "All questions must be open-ended descriptive. Set options=[] and correctAnswer=null. Include expected_answer key.",
        "mixed":       "Mix of MCQ (70%) and descriptive (30%). MCQ has 4 options; descriptive has options=[] and correctAnswer=null.",
    }.get(q_type.lower(), "Single correct MCQ with 4 options.")

    short_instr = exam_instructions[:400] if len(exam_instructions) > 400 else exam_instructions

    prompt = f"""Generate {safe_count} {q_type.upper()} questions for {name} exam.
Difficulty: {difficulty.upper()} ({difficulty_context})
Subjects: {subjects_hint}
Instructions: {short_instr}

Output ONLY a JSON array. Rules:
- Each question must be specific to {name} (not generic)
- MCQ: 4 options, correctAnswer is 0-based index
- Keep explanation under 30 words
- No LaTeX, write math as plain text
- All {safe_count} questions must be different topics

[{{"id":"q1","type":"{q_type}","text":"question","options":["A","B","C","D"],"correctAnswer":0,"explanation":"brief","topic":"topic","subject":"subject","difficulty":"{difficulty}","marks":{marks_per_q}}}]

Now generate exactly {safe_count} questions in the same JSON array format:"""

    try:
        raw = _call(prompt)
        print(f"\n[AI RAW RESPONSE] (first 500 chars):\n{raw[:500]}\n")

        clean     = _clean_raw(raw)
        json_text = _extract_json_array(clean)
        questions = json.loads(json_text)

        if not isinstance(questions, list) or len(questions) == 0:
            raise ValueError("Empty questions list from AI")

        questions = _sanitize_questions(questions, name, q_type)

        # Force correct difficulty on all questions (in case AI ignored it)
        for q in questions:
            q["difficulty"] = difficulty.capitalize()

        print(f"[AI] Generated {len(questions)} real {name} ({difficulty}) questions")

        final_questions = questions[:safe_count]
        # FIX: scale duration to the actual number of questions returned,
        # using this exam's real seconds-per-question (secs_per_q), instead
        # of a fixed value. Minimum 5 minutes so a 1-2 question test isn't
        # absurdly short.
        suggested_minutes = max(5, round(secs_per_q * len(final_questions) / 60))

        return {
            "questions": final_questions,
            "source":    "openrouter",
            "ai_error":  None,
            "suggested_duration_minutes": suggested_minutes,
        }

    except Exception as e:
        err = str(e)
        print(f"[AI] FAILED for {name}: {err}")

        # FIX: this fallback list now actually gets returned under "questions",
        # matching the shape callers expect (previously it was built then
        # discarded, and the function returned a mismatched {"practice": ...}
        # dict instead — that was the root cause of "failed to generate questions").
        fallback = [
            {
                "id":            f"fallback_{i}",
                "type":          "mcq",
                "text":          f"[AI Unavailable] Sample {name} Question {i+1}",
                "question_text": f"[AI Unavailable] Sample {name} Question {i+1}",
                "options":       ["Option A", "Option B", "Option C", "Option D"],
                "correctAnswer": 0,
                "explanation":   "AI service unavailable. Please try again.",
                "topic":         name,
                "subject":       name,
                "difficulty":    difficulty,
                "marks":         marks_per_q,
            }
            for i in range(min(safe_count, 5))
        ]

        # Prefer the curated question bank if one exists for this exam/topic;
        # otherwise use the generic placeholder fallback above.
        try:
            bank = get_curated_mcq(name, difficulty, safe_count)
        except Exception:
            bank = []

        final_questions = bank if bank else fallback
        suggested_minutes = max(5, round(secs_per_q * len(final_questions) / 60))

        return {
            "questions": final_questions,
            "source":    "bank" if bank else "fallback",
            "ai_error":  err,
            "suggested_duration_minutes": suggested_minutes,
        }


# ─────────────────────────────────────────────────────────────
# 3. Online Test Generation
# ─────────────────────────────────────────────────────────────

def generate_full_test(exam_name: str, duration: int = 60) -> dict:
    prompt = f"""
Create a comprehensive online examination for: {exam_name}
Duration: {duration} minutes

Return ONLY valid JSON:
{{
  "metadata": {{
    "exam_name": "{exam_name}",
    "total_questions": 15,
    "mcq_count": 10,
    "descriptive_count": 5,
    "total_marks": 50
  }},
  "sections": [
    {{
      "title": "Section A – Multiple Choice",
      "type": "mcq",
      "marks_per_question": 2,
      "questions": [
        {{
          "id": "mcq_1",
          "text": "Question text",
          "options": ["A", "B", "C", "D"],
          "correctAnswer": 0,
          "explanation": "Explanation",
          "topic": "topic",
          "difficulty": "medium",
          "marks": 2
        }}
      ]
    }}
  ]
}}
"""
    try:
        raw = _call(prompt)
        return _parse_json(raw)
    except Exception as e:
        return {"error": str(e), "metadata": {"exam_name": exam_name}}


# ─────────────────────────────────────────────────────────────
# 4. Descriptive Answer Evaluation
# ─────────────────────────────────────────────────────────────

def evaluate_descriptive_answer(question: str, answer: str, max_marks: int = 10) -> dict:
    prompt = f"""
You are an expert exam evaluator.

Question: {question}
Student Answer: {answer}
Maximum Marks: {max_marks}

Return ONLY valid JSON:
{{
  "score": <0-{max_marks}>,
  "percentage": <0-100>,
  "feedback": "Constructive feedback",
  "strengths": ["strength 1"],
  "improvements": ["improvement 1"],
  "key_concepts_covered": ["concept1"],
  "missing_concepts": ["missing1"]
}}
"""
    try:
        raw = _call(prompt)
        result = _parse_json(raw)
        result["score"] = min(max(float(result.get("score", 0)), 0), max_marks)
        return result
    except Exception as e:
        if not answer or len(answer.strip()) < 10:
            return {"score": 0, "percentage": 0, "feedback": "No answer provided.",
                    "strengths": [], "improvements": []}
        return {"score": round(max_marks * 0.5, 1), "percentage": 50,
                "feedback": "Auto-evaluated.", "strengths": [], "improvements": []}


# ─────────────────────────────────────────────────────────────
# 5. Exam Report Insights
# ─────────────────────────────────────────────────────────────

def generate_exam_report_insights(exam_name, performance_data, question_analysis) -> dict:
    prompt = f"""
Analyse this student's exam performance for {exam_name}.
Score: {performance_data.get('marks_percentage', 0):.1f}%
Correct: {performance_data.get('correct_answers', 0)}/{performance_data.get('total_questions', 0)}

Return ONLY valid JSON:
{{
  "performance_level": "Excellent|Very Good|Good|Satisfactory|Needs Improvement",
  "summary": "2-sentence assessment",
  "strengths": ["strength1"],
  "weaknesses": ["weakness1"],
  "insights": ["insight1", "insight2"],
  "recommendations": ["rec1", "rec2"],
  "study_plan": {{"immediate": "today", "short_term": "this week", "long_term": "monthly"}}
}}
"""
    try:
        raw = _call(prompt)
        return _parse_json(raw)
    except Exception as e:
        pct = performance_data.get("marks_percentage", 0)
        return {
            "performance_level": "Excellent" if pct >= 85 else "Good" if pct >= 65 else "Needs Improvement",
            "summary": f"Student scored {pct:.1f}% on {exam_name}.",
            "strengths": [], "weaknesses": [],
            "insights": ["Review incorrect answers"],
            "recommendations": ["Practice regularly"],
            "study_plan": {"immediate": "Review mistakes", "short_term": "Practice daily", "long_term": "Revision"},
        }


# ─────────────────────────────────────────────────────────────
# 6. Personalised Practice
# ─────────────────────────────────────────────────────────────

def generate_personalised_practice(
    country, exam_type, weak_areas, strong_areas,
    target_score=80, has_history=False,
) -> dict:
    context = (
        f"Weak areas: {', '.join(weak_areas) if weak_areas else 'General'}\n"
        f"Strong areas: {', '.join(strong_areas) if strong_areas else 'General'}\n"
        f"Target: {target_score}%"
    ) if has_history else "New student — create diagnostic session."

    prompt = f"""
You are an adaptive AI for {exam_type} prep ({country}).
{context}

Create 10-12 question personalised practice session.
Return ONLY valid JSON:
{{
  "session_title": "Personalised Practice – {exam_type}",
  "session_type": "adaptive",
  "message": "Encouraging message",
  "total_questions": 10,
  "estimated_minutes": 20,
  "focus_topics": ["topic1"],
  "questions": [
    {{
      "question_number": 1,
      "question_text": "Full question",
      "text": "Full question",
      "topic": "Topic",
      "difficulty": "Easy|Medium|Hard",
      "learning_objective": "What this tests",
      "max_score": 5,
      "hints": ["Hint"]
    }}
  ]
}}
"""
    try:
        raw = _call(prompt)
        data = _parse_json(raw)
        if not isinstance(data, dict) or not data.get("questions"):
            raise ValueError("Invalid response")
        data["questions"] = _sanitize_questions(data["questions"], exam_type, "descriptive")
        return data
    except Exception as e:
        fallback_questions = get_curated_mcq(exam_type, "medium", 10)
        return {
            "session_title": f"Practice – {exam_type}",
            "session_type": "fallback",
            "message": "Questions from question bank",
            "total_questions": len(fallback_questions),
            "estimated_minutes": 20,
            "focus_topics": [exam_type],
            "questions": [
                {
                    "question_number": i + 1,
                    "question_text": q.get("text", ""),
                    "text": q.get("text", ""),
                    "topic": q.get("topic", exam_type),
                    "difficulty": q.get("difficulty", "medium"),
                    "learning_objective": "Strengthen core concepts",
                    "max_score": 5,
                    "hints": [],
                }
                for i, q in enumerate(fallback_questions)
            ],
        }


# ─────────────────────────────────────────────────────────────
# 6b. AI Tutor – Explain Concepts  (required by quiz.py /explain route)
# ─────────────────────────────────────────────────────────────

def explain_concept(concept: str, level: str = "intermediate") -> dict:
    """Explain a concept clearly. Called by quiz.py /explain route."""
    prompt = f"""You are a friendly AI tutor. Explain this concept clearly.

Concept: {concept}
Student Level: {level}

Return ONLY valid JSON:
{{
  "concept": "{concept}",
  "simple_explanation": "ELI5 explanation in 2-3 sentences",
  "detailed_explanation": "Comprehensive explanation with context",
  "key_points": ["point1", "point2", "point3"],
  "examples": ["Real-world example 1", "Example 2"],
  "common_mistakes": ["Mistake students often make"],
  "memory_tip": "Mnemonic or memory aid",
  "related_concepts": ["related1", "related2"],
  "practice_question": "A practice question to test understanding"
}}"""
    try:
        raw = _call(prompt)
        return _parse_json(raw)
    except Exception as e:
        print(f"[AI] explain_concept failed: {e}")
        # FIX: was `return {{ ... }}` — double braces made this a SET containing
        # a dict, which crashes with "TypeError: unhashable type: 'dict'" the
        # moment this fallback path ran. Single braces = a normal dict.
        return {
            "concept": concept,
            "simple_explanation": _ai_unavailable_msg(e, "AI tutor"),
            "detailed_explanation": "",
            "key_points": [],
            "examples": [],
            "common_mistakes": [],
            "memory_tip": "",
            "related_concepts": [],
            "practice_question": "",
            "ai_error": str(e),
        }


# ─────────────────────────────────────────────────────────────
# 7. Performance Analytics
# ─────────────────────────────────────────────────────────────

def analyse_performance_trends(results: list[dict]) -> dict:
    if not results:
        return {"trend": "no_data", "insights": [], "recommendations": []}
    summary = [{"exam": r.get("exam_name"), "score": r.get("score", 0)} for r in results[-10:]]
    prompt = f"""
Analyse student performance: {json.dumps(summary)}
Return ONLY valid JSON:
{{
  "trend": "improving|declining|stable|inconsistent",
  "average_score": 0,
  "insights": ["insight"],
  "recommendations": ["action"]
}}
"""
    try:
        return _parse_json(_call(prompt))
    except Exception:
        scores = [r.get("score", 0) for r in results]
        avg = sum(scores) / len(scores) if scores else 0
        return {"trend": "stable", "average_score": round(avg, 1),
                "insights": [f"Average: {avg:.1f}%"], "recommendations": ["Keep practising"]}


# ─────────────────────────────────────────────────────────────
# 8. AI Tutor Chat
# ─────────────────────────────────────────────────────────────

def ai_tutor_chat(messages: list[dict], subject: str = "General") -> dict:
    history = "\n".join(
        f"{'Student' if m['role'] == 'user' else 'Tutor'}: {m['content']}"
        for m in messages[-10:]
    )
    prompt = f"""
You are an expert AI tutor for {subject}.
{history}

Return ONLY valid JSON:
{{
  "reply": "Your response",
  "follow_up_question": null,
  "key_concept": null,
  "confidence_check": null
}}
"""
    try:
        return _parse_json(_call(prompt))
    except Exception as e:
        return {"reply": _ai_unavailable_msg(e, "AI tutor"),
                "follow_up_question": None, "key_concept": None,
                "confidence_check": None, "ai_error": str(e)}


# ─────────────────────────────────────────────────────────────
# 9. Smart Recommendations
# ─────────────────────────────────────────────────────────────

def generate_smart_recommendations(
    weak_topics, strong_topics, exam_type, avg_score, learning_style="visual"
) -> dict:
    prompt = f"""
Student: {exam_type}, avg {avg_score:.1f}%, weak: {weak_topics}, learning: {learning_style}
Return ONLY valid JSON:
{{
  "priority_topics": ["topic1"],
  "study_strategies": [{{"strategy": "name", "description": "desc", "time_required": "15 min/day", "effectiveness": "high"}}],
  "resources": [],
  "weekly_plan": [],
  "milestone": "Goal for 2 weeks",
  "motivational_message": "Message"
}}
"""
    try:
        return _parse_json(_call(prompt))
    except Exception as e:
        return {
            "priority_topics": weak_topics[:3] or ["Core Concepts"],
            "study_strategies": [{"strategy": "Spaced Repetition", "description": "Review at intervals",
                                   "time_required": "15 min/day", "effectiveness": "high"}],
            "resources": [], "weekly_plan": [],
            "milestone": "Improve by 10% in 2 weeks",
            "motivational_message": "Every expert was once a beginner. Keep going!",
        }


# ─────────────────────────────────────────────────────────────
# 10. Risk Prediction
# ─────────────────────────────────────────────────────────────

def predict_performance_risk(results: list[dict], upcoming_exam: str = "") -> dict:
    if not results:
        return {"risk_level": "unknown", "alerts": [], "predictions": []}
    scores = [r.get("score", 0) for r in results]
    avg = sum(scores) / len(scores) if scores else 0
    risk = "low" if avg >= 70 else "medium" if avg >= 50 else "high"
    return {
        "risk_level": risk,
        "pass_probability": min(95, max(5, avg + 10)),
        "trend": "stable",
        "alerts": [{"type": "info", "message": f"Current average: {avg:.1f}%", "topic": "Overall"}],
        "predictions": [],
        "intervention_plan": "Review weak areas daily and take mock tests weekly.",
    }


# ─────────────────────────────────────────────────────────────
# 11. Adaptive Difficulty
# ─────────────────────────────────────────────────────────────

def get_adaptive_difficulty(recent_accuracy: float, current_difficulty: str) -> str:
    if recent_accuracy >= 0.85 and current_difficulty != "hard":
        return "hard" if current_difficulty == "medium" else "medium"
    elif recent_accuracy < 0.5 and current_difficulty != "easy":
        return "easy" if current_difficulty == "medium" else "medium"
    return current_difficulty


def generate_adaptive_questions(topic, answered, target_count=5) -> list[dict]:
    correct  = sum(1 for a in answered if a.get("correct"))
    accuracy = correct / (len(answered) or 1)
    last_diff = answered[-1].get("difficulty", "medium") if answered else "medium"
    next_diff = get_adaptive_difficulty(accuracy, last_diff)
    weak = [a.get("topic", topic) for a in answered if not a.get("correct")]
    focus = weak[-2:] if weak else [topic]
    return generate_questions(
        topic=f"{topic} — focus: {', '.join(focus)}",
        q_type="mcq", difficulty=next_diff, count=target_count,
        extra_instructions=f"Accuracy: {accuracy*100:.0f}%. Focus on: {', '.join(focus)}.",
    )


# ─────────────────────────────────────────────────────────────
# 12. Class Insights
# ─────────────────────────────────────────────────────────────

def generate_class_insights(student_results: list[dict]) -> dict:
    if not student_results:
        return {}
    try:
        prompt = f"""
Class of {len(student_results)} students. Top 10: {json.dumps(student_results[:10])}
Return ONLY valid JSON:
{{
  "class_health": "excellent|good|needs_attention|critical",
  "common_weak_topics": ["topic1"],
  "teaching_suggestions": ["suggestion"],
  "class_summary": "2-sentence summary"
}}
"""
        return _parse_json(_call(prompt))
    except Exception as e:
        return {"class_health": "unknown", "teaching_suggestions": [],
                "class_summary": "Analysis unavailable.", "ai_error": str(e)}
