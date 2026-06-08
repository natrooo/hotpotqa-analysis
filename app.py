# -*- coding: utf-8 -*-
from flask import Flask, render_template, request, jsonify
import sqlite3
import os

app = Flask(__name__)
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hotpotqa.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

# ==================== ROUTES ====================

@app.route('/')
def index():
    return render_template('index.html')

# ---- Search & Multi-hop Retrieval ----
@app.route('/api/search')
def search():
    """Multi-hop search: keyword + type filter + cluster filter"""
    keyword = request.args.get('q', '').strip()
    qtype = request.args.get('type', '')
    cluster = request.args.get('cluster', '')
    page = int(request.args.get('page', 1))
    per_page = 10

    conn = get_db()
    cur = conn.cursor()

    conditions = []
    params = []

    if keyword:
        conditions.append("""
            q.rowid IN (
                SELECT rowid FROM questions_fts WHERE questions_fts MATCH ?
            )
        """)
        params.append(keyword)

    if qtype:
        conditions.append("q.type = ?")
        params.append(qtype)

    if cluster:
        conditions.append("c.cluster_id = ?")
        params.append(int(cluster))

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    # Count total
    if cluster:
        cur.execute(f"SELECT COUNT(*) FROM questions q LEFT JOIN clusters c ON q.id = c.question_id WHERE {where_clause}", params)
    else:
        cur.execute(f"SELECT COUNT(*) FROM questions q LEFT JOIN clusters c ON q.id = c.question_id WHERE {where_clause}", params)
    total = cur.fetchone()[0]

    # Fetch page
    offset = (page - 1) * per_page
    if cluster:
        cur.execute(f"""
            SELECT q.*, c.cluster_id FROM questions q
            LEFT JOIN clusters c ON q.id = c.question_id
            WHERE {where_clause}
            ORDER BY q.id LIMIT ? OFFSET ?
        """, params + [per_page, offset])
    else:
        cur.execute(f"""
            SELECT q.*, c.cluster_id FROM questions q
            LEFT JOIN clusters c ON q.id = c.question_id
            WHERE {where_clause}
            ORDER BY q.id LIMIT ? OFFSET ?
        """, params + [per_page, offset])

    rows = cur.fetchall()

    results = []
    for row in rows:
        qid = row['id']
        # Get contexts with sentences
        cur.execute("""
            SELECT c.id as ctx_id, c.doc_index, c.doc_title, c.is_supporting
            FROM contexts c WHERE c.question_id = ? ORDER BY c.doc_index
        """, (qid,))
        contexts = []
        for ctx in cur.fetchall():
            cur.execute("""
                SELECT sent_index, sent_text, is_supporting_fact
                FROM sentences WHERE context_id = ? ORDER BY sent_index
            """, (ctx['ctx_id'],))
            sents = [dict(s) for s in cur.fetchall()]
            contexts.append({
                'doc_index': ctx['doc_index'],
                'doc_title': ctx['doc_title'],
                'is_supporting': bool(ctx['is_supporting']),
                'sentences': sents
            })

        results.append({
            'id': qid,
            'question': row['question'],
            'answer': row['answer'],
            'type': row['type'],
            'level': row['level'],
            'cluster_id': row['cluster_id'],
            'contexts': contexts
        })

    conn.close()

    return jsonify({
        'total': total,
        'page': page,
        'per_page': per_page,
        'results': results
    })

# ---- Cluster Data API ----
@app.route('/api/clusters')
def get_clusters():
    """Return all cluster data for visualization"""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT q.id, q.question, q.answer, q.type, c.cluster_id, c.coord_x, c.coord_y
        FROM clusters c JOIN questions q ON c.question_id = q.id
    """)
    data = [dict(r) for r in cur.fetchall()]

    # Cluster terms
    cur.execute("SELECT cluster_id, term, weight FROM cluster_terms ORDER BY cluster_id, weight DESC")
    terms_raw = cur.fetchall()
    terms = {}
    for t in terms_raw:
        cid = str(t['cluster_id'])
        if cid not in terms:
            terms[cid] = []
        terms[cid].append({'term': t['term'], 'weight': t['weight']})

    conn.close()
    return jsonify({'points': data, 'cluster_terms': terms})

# ---- Statistics API ----
@app.route('/api/stats')
def get_stats():
    """Return dataset statistics"""
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) as total FROM questions")
    total = cur.fetchone()['total']

    cur.execute("SELECT type, COUNT(*) as cnt FROM questions GROUP BY type")
    type_dist = {r['type']: r['cnt'] for r in cur.fetchall()}

    cur.execute("SELECT level, COUNT(*) as cnt FROM questions GROUP BY level")
    level_dist = {r['level']: r['cnt'] for r in cur.fetchall()}

    cur.execute("SELECT cluster_id, COUNT(*) as cnt FROM clusters GROUP BY cluster_id ORDER BY cluster_id")
    cluster_dist = {str(r['cluster_id']): r['cnt'] for r in cur.fetchall()}

    cur.execute("""
        SELECT c.cluster_id, q.type, COUNT(*) as cnt
        FROM clusters c JOIN questions q ON c.question_id = q.id
        GROUP BY c.cluster_id, q.type ORDER BY c.cluster_id, q.type
    """)
    cluster_type = [dict(r) for r in cur.fetchall()]

    conn.close()
    return jsonify({
        'total': total,
        'type_distribution': type_dist,
        'level_distribution': level_dist,
        'cluster_distribution': cluster_dist,
        'cluster_type_breakdown': cluster_type
    })

# ---- CRUD: Get single question with full context ----
@app.route('/api/question/<qid>')
def get_question(qid):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM questions WHERE id = ?", (qid,))
    q = cur.fetchone()
    if not q:
        conn.close()
        return jsonify({'error': 'Not found'}), 404

    cur.execute("SELECT * FROM contexts WHERE question_id = ? ORDER BY doc_index", (qid,))
    contexts = []
    for ctx in cur.fetchall():
        cur.execute("SELECT * FROM sentences WHERE context_id = ? ORDER BY sent_index", (ctx['id'],))
        sents = [dict(s) for s in cur.fetchall()]
        ctx_dict = dict(ctx)
        ctx_dict['sentences'] = sents
        contexts.append(ctx_dict)

    result = dict(q)
    result['contexts'] = contexts

    conn.close()
    return jsonify(result)

# ---- CRUD: Count records ----
@app.route('/api/count')
def count():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) as cnt FROM questions")
    total = cur.fetchone()['cnt']
    cur.execute("SELECT COUNT(*) as cnt FROM contexts")
    ctx = cur.fetchone()['cnt']
    cur.execute("SELECT COUNT(*) as cnt FROM sentences")
    sents = cur.fetchone()['cnt']
    conn.close()
    return jsonify({'questions': total, 'contexts': ctx, 'sentences': sents})

# ---- SQL Query (for demo) ----
@app.route('/api/sql', methods=['POST'])
def run_sql():
    data = request.get_json()
    sql = data.get('sql', '').strip()
    if not sql:
        return jsonify({'error': 'Empty query'}), 400
    # Only allow SELECT for safety
    if not sql.upper().startswith('SELECT'):
        return jsonify({'error': 'Only SELECT queries allowed'}), 403
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(sql)
        rows = [list(r) for r in cur.fetchall()]
        columns = [desc[0] for desc in cur.description] if cur.description else []
        conn.close()
        return jsonify({'columns': columns, 'rows': rows})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

# ---- Static info page ----
@app.route('/about')
def about():
    return render_template('about.html')

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)
