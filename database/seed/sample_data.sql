INSERT INTO questions (id, slug, text) VALUES
    ('a0000000-0000-0000-0000-000000000001', 'what-is-the-boiling-point-of-water', 'What is the boiling point of water at sea level?');

INSERT INTO answer_versions (id, question_id, version, status, final_answer, confidence) VALUES
    ('b0000000-0000-0000-0000-000000000001', 'a0000000-0000-0000-0000-000000000001', 1, 'sealed', 'The boiling point of water at sea level (1 atm) is 100 degrees Celsius (212 degrees Fahrenheit).', 0.99);
