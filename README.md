\# VektorSync — Offline Sync Conflict Engine

\*\*Author:\*\* Sai Venkata Reddy  

\*\*Stack:\*\* Python 3.14, FastAPI, SQLite (SQLAlchemy), scikit-learn, PyTest



\---



\## What Problem Does This Solve?



When multiple devices go offline and edit the same document, bringing them back online causes serious synchronization headaches. 



Most simple backends use \*\*Last-Write-Wins (LWW)\*\* based on wall-clock timestamps. In practice, device clocks drift, and network latency can make a late edit look early. This leads to silent data loss where one user's work gets wiped without any warning.



\*\*VektorSync\*\* solves this without relying on device timestamps:



1\. \*\*Vector Clocks (Logical Time):\*\* Instead of trusting device clocks, each device keeps a logical counter. The server uses vector comparisons to determine if an edit is a clean progression or an offline split.

2\. \*\*3-Way Field Merging:\*\* Compares the original version (when the device went offline) against both the current server state and the incoming change. If Device A edited `status` and Device B edited `lead`, both updates are kept automatically.

3\. \*\*Semantic Text Arbitration (TF-IDF + Cosine Similarity):\*\* If two users edit the same text sentence concurrently, a basic diff marks it as broken. VektorSync vectorizes both strings using character n-grams. If the cosine similarity is $\\ge 0.80$ (e.g., minor wording polish or fixing typos), it merges them safely. If they diverge or contradict each other, it halts and flags a conflict.

4\. \*\*Network Idempotency:\*\* Mobile retries won't accidentally increment clocks or duplicate changes thanks to unique idempotency keys recorded in an append-only journal.

5\. \*\*Version Snapshots \& Rollback:\*\* Every approved change is saved as an immutable snapshot, allowing users to view the entire audit history and restore any older version.



\---



\## Required Sync Outcomes



As specified in Task 6, every sync response maps strictly to one of four outcomes:



| Outcome | When It Happens | HTTP Status |

| :--- | :--- | :--- |

| \*\*`Change accepted`\*\* | The client edit builds directly on top of the server's current state (linear fast-forward). | `200 OK` |

| \*\*`Changes merged`\*\* | Edits happened concurrently offline, but touched different fields or passed the semantic similarity check. | `200 OK` |

| \*\*`Conflict requiring resolution`\*\* | Concurrent edits touched the same scalar field or had conflicting text meanings. Both versions are preserved. | `409 Conflict` |

| \*\*`Change rejected`\*\* | Stale, malformed, or invalid payloads that cannot be processed. | `400 Bad Request` |



\---



\## API Endpoints



\- `POST /api/v1/sync/push` — Push offline mutations (handles vector clocks, 3-way merge, and ML arbitration).

\- `GET /api/v1/sync/pull/{document\_id}` — Fetch latest document state and clock vector.

\- `GET /api/v1/lineage/{document\_id}/history` — Retrieve full historical version audit trail.

\- `POST /api/v1/lineage/{document\_id}/restore` — Revert the document to any previous snapshot version.

\- `GET /health` — Health check endpoint.



\---



\## Quickstart \& Verification



\### 1. Install Dependencies

```bash

pip install -r requirements.txt

