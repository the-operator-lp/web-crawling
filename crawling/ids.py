# ID counters and generators
novel_id_counter = 0
chapter_id_counter = 0
genre_id_counter = 0

def generate_novel_id():
    global novel_id_counter
    novel_id_counter += 1
    return f"NOV{novel_id_counter:07d}"

def generate_chapter_id():
    global chapter_id_counter
    chapter_id_counter += 1
    return f"CHA{chapter_id_counter:07d}"

def generate_genre_id():
    global genre_id_counter
    genre_id_counter += 1
    return f"GEN{genre_id_counter:07d}"
