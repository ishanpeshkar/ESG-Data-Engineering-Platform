0. (If needed) Re-map short path for Windows long-path issues: `subst X: "D:\Ishan-Peshkar-Personel\coding\Projects\ESG-DataEngineering-Platform\esg-data-platform"` then `cd X:\`

# How to Start This Project (after time away)   

1. Open a terminal in the project root, activate the venv: `.venv\Scripts\activate`
2. To run the pipeline manually: see `INSTRUCTIONS.md` section 3 for the 4 commands (extract → clean → validate → gold)
3. To use Airflow: `cd airflow` then `docker compose up -d`, open http://localhost:8080 (login: airflow/airflow)
4. When done: `cd airflow` then `docker compose down` (stops containers, saves resources)
5. Check `PROJECT_LOG.md` if you forget *why* something was built a certain way
6. Check `INSTRUCTIONS.md` for full command reference and current phase status


AIRFLOW UI
USERNAME - airflow
Password - airflow