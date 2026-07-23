#include "fetch_pool.h"
#include <process.h>
#include <string.h>

typedef struct {
    FetchPool *pool;
    int        i0, i1;
} FetchChunk;

void fetch_pool_init(FetchPool *p) {
    memset(p, 0, sizeof(*p));
}

int fetch_pool_add(FetchPool *p, const wchar_t *url, char *body, size_t cap) {
    FetchSlot *s;

    if (!p || !url || !body || cap < 64 || p->n >= FETCH_POOL_MAX) return 0;
    s = &p->slot[p->n++];
    lstrcpynW(s->url, url, (int)(sizeof(s->url) / sizeof(s->url[0])));
    s->body = body;
    s->body_cap = cap;
    s->len = 0;
    s->err = 0;
    s->status = 0;
    s->ok = 0;
    return 1;
}

static unsigned __stdcall fetch_chunk_worker(void *arg) {
    FetchChunk *c = (FetchChunk *)arg;
    IngestSession *sess = ingest_session_open();
    int i;

    if (!sess) return 1;
    for (i = c->i0; i < c->i1; i++) {
        FetchSlot *s = &c->pool->slot[i];
        s->ok = ingest_session_get(sess, s->url, s->body, s->body_cap, &s->len);
        s->err = ingest_last_error();
        s->status = ingest_last_status();
    }
    ingest_session_close(sess);
    return 0;
}

int fetch_pool_run(FetchPool *p, IngestSession *sess) {
    FetchChunk chunks[4];
    HANDLE th[4];
    unsigned tid;
    int i, nch = 0, chunk_sz, ok = 0;

    if (!p || p->n <= 0) return 0;

    if (p->n <= 3) {
        for (i = 0; i < p->n; i++) {
            FetchSlot *s = &p->slot[i];
            s->ok = ingest_session_get(sess, s->url, s->body, s->body_cap, &s->len);
            s->err = ingest_last_error();
            s->status = ingest_last_status();
            if (s->ok) ok++;
        }
        return ok;
    }

    chunk_sz = (p->n + 3) / 4;
    for (i = 0; i < p->n; i += chunk_sz) {
        chunks[nch].pool = p;
        chunks[nch].i0 = i;
        chunks[nch].i1 = i + chunk_sz;
        if (chunks[nch].i1 > p->n) chunks[nch].i1 = p->n;
        th[nch] = (HANDLE)_beginthreadex(NULL, 0, fetch_chunk_worker, &chunks[nch], 0, &tid);
        if (th[nch]) nch++;
        else break;
    }
    if (nch == 0) return 0;

    WaitForMultipleObjects((DWORD)nch, th, TRUE, 120000);
    for (i = 0; i < nch; i++)
        CloseHandle(th[i]);
    for (i = 0; i < p->n; i++)
        if (p->slot[i].ok) ok++;
    return ok;
}
