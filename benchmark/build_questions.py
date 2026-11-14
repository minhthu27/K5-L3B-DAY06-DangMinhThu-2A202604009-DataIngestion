"""Sinh benchmark/questions.json từ danh sách bên dưới.
Chạy từ thư mục gốc repo: python benchmark/build_questions.py
"""
import json
import pathlib

S = "soc3e"
# id, split, type, question, expected_answer, gold_page (số trang PDF gốc), evidence_quote, filter
Q = [
    ("d01", "dev", "truc_tiep", "How do sociologists define sociology?",
     "The scientific and systematic study of groups and group interactions, societies and social interactions.", 20,
     "Sociology is the scientific and systematic study of groups and group interactions, societies and social interactions", None),
    ("d02", "dev", "dien_dat_lai", "Which book was the first to carry the word sociology in its title, and who wrote it?",
     "The Study of Sociology (1873) by Herbert Spencer.", 25,
     "published The Study of Sociology, the first book with the term", None),
    ("d03", "dev", "dieu_kien", "What is the difference between consequences of a social process that are intended and those that are not?",
     "Manifest functions are sought or anticipated; latent functions are unsought consequences.", 30,
     "Manifest functions are the consequences of a social process that are sought or anticipated, while latent functions are the unsought consequences of a social process", None),
    ("d04", "dev", "truc_tiep", "Who founded the first European university department of sociology, where, and when?",
     "Emile Durkheim, University of Bordeaux, 1895.", 26,
     "establishing the first European department of sociology at the University of Bordeaux in 1895", None),
    ("d05", "dev", "dien_dat_lai", "What groundbreaking empirical study did W.E.B. Du Bois carry out in Philadelphia?",
     "A 1896-1897 study of the African American community in Philadelphia based on hundreds of interviews.", 27,
     "His groundbreaking 1896-1897 study of the African American community in Philadelphia incorporated hundreds of interviews", None),
    ("d06", "dev", "dien_dat_lai", "Which early American sociologist argued that people compare themselves to others to stay within social standards?",
     "Charles Horton Cooley (the looking-glass self).", 28,
     "Charles Horton Cooley posited that individuals compare themselves to others in order to check themselves against social standards and remain part of the group", None),
    ("d07", "dev", "truc_tiep", "How many steps does the scientific method have in sociological research?",
     "Six steps.", 48,
     "It involves a series of six prescribed steps", None),
    ("d08", "dev", "loc_metadata", "In the research process, what separates the independent variable from the dependent variable?",
     "The independent variable is the cause of the change; the dependent variable is the effect.", 50,
     "an independent variable (IV), which is the cause of the change, and a dependent variable (DV), which is the effect", {"chapter": "ch2"}),
    ("d09", "dev", "dieu_kien", "What does validity mean for a research study, compared with reliability?",
     "Validity is how well the study measures what it was designed to measure; reliability is how likely results are to be replicated.", 51,
     "validity, which refers to how well the study measures what it was designed to measure", None),
    ("d10", "dev", "truc_tiep", "What is a random sample?",
     "A sample in which every person in the population has the same chance of being chosen.", 54,
     "In a random sample, every person in a population has the same chance of being chosen for the study", None),
    ("d11", "dev", "dien_dat_lai", "Why might participants act unnaturally when they know a study is observing them?",
     "The Hawthorne effect: people change behavior because they know they are being watched.", 63,
     "which occurs when people change their behavior because they know they are being watched as part of a study", None),
    ("d12", "dev", "truc_tiep", "What is a case study and what is its main criticism?",
     "An in-depth analysis of a single event, situation or individual; it cannot support generalized conclusions.", 62,
     "A case study is an in-depth analysis of a single event, situation, or individual", None),
    ("d13", "dev", "chi_tiet", "How many traffic citations did the fifteen drivers in the Heussenstamm bumper-sticker experiment collect?",
     "Thirty-three citations in seventeen days.", 64,
     "the fifteen drivers had collected a total of thirty-three traffic citations", None),
    ("d14", "dev", "loc_metadata", "What does Weber's concept of verstehen mean?",
     "Understanding a social world deeply from an insider's point of view.", 26,
     "verstehen, a German word that means to understand in a deep way", {"chapter": "ch1"}),
    ("d15", "dev", "loc_metadata", "Which practice should researchers follow so personal values do not distort how results are interpreted and published?",
     "Value neutrality: staying impartial, without bias or judgment, during the study and in publishing results.", 65,
     "value neutrality, a practice of remaining impartial, without bias or judgment, during the course of a study and in publishing results", {"chapter": "ch2"}),
    ("t01", "test", "dien_dat_lai", "How did Erving Goffman compare social interaction to the theater?",
     "Dramaturgical analysis: individuals are actors in a play who follow cultural scripts.", 34,
     "Goffman used theater as an analogy for social interaction", None),
    ("t02", "test", "dieu_kien", "Whose research did the Supreme Court cite in the Brown v. Board of Education decision to show segregation harms minority students?",
     "Kenneth and Mamie Clark (the doll test).", 35,
     "the Supreme Court cited the research of the husband-and-wife team of social scientists, Kenneth and Mamie Clark", None),
    ("t03", "test", "loc_metadata", "What is a hypothesis in the six-step research process?",
     "An explanation for a phenomenon based on a conjecture about the relationship between it and one or more causal factors.", 50,
     "A hypothesis is an explanation for a phenomenon based on a conjecture about the relationship between the phenomenon and one or more causal factors", {"chapter": "ch2"}),
    ("t04", "test", "truc_tiep", "What is the ASA?",
     "The American Sociological Association, the major professional organization of sociologists in North America.", 65,
     "The American Sociological Association, or ASA, is the major professional organization of sociologists in North America", None),
    ("t05", "test", "dieu_kien", "Why is secondary data analysis called nonreactive or unobtrusive research?",
     "Because it does not involve direct contact with subjects and does not alter their behavior.", 64,
     "it is nonreactive research (or unobtrusive research), meaning that it does not involve direct contact with subjects", None),
]

out = [
    {"id": i, "split": sp, "type": ty, "question": q, "expected_answer": a,
     "gold_source_id": S, "gold_page": pg, "evidence_quote": ev, "filter": flt}
    for (i, sp, ty, q, a, pg, ev, flt) in Q
]
pathlib.Path(__file__).with_name("questions.json").write_text(
    json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
print(len(out), "questions written")
