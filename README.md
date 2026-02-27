# Money Saver

Personal budget tracker with two versions: a desktop app (Tkinter) and a web app (Streamlit + Supabase).

## Features

- Track savings across custom categories (allocate from a distributable pool)
- Track expenses with salary/income input and category spending
- Transfer funds between savings and expenses
- Multi-currency support with configurable exchange rates
- Per-category preset notes, transaction edit/delete, Excel export

## Structure

```
desktop/   - Tkinter app, local JSON storage
web/       - Streamlit app, Supabase (Postgres) with email auth
```

## Web app setup

1. Create a Supabase project and add two tables: `transactions` and `settings`
2. Set secrets in `.streamlit/secrets.toml`:
   ```toml
   SUPABASE_URL = "https://..."
   SUPABASE_KEY = "..."
   ```
3. Install and run:
   ```bash
   pip install -r web/requirements.txt
   streamlit run web/app.py
   ```

## Desktop app setup

```bash
pip install openpyxl
python desktop/main.py
```

## Tech

- Web: Streamlit, Supabase (supabase-py), openpyxl
- Desktop: Tkinter (stdlib), local JSON, openpyxl
