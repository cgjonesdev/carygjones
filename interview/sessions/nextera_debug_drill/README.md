# NextEra debug drill (Jake’s team style)

Practice for the format Dinesh described (Sep 17, 2026):

1. Run the failing test and find the root cause (talk out loud).
2. Fix only what’s broken — then discuss what you’d improve if you owned it.
3. Answer: “How would you make this production-ready?”

```bash
cd interview/sessions/nextera_debug_drill
python3 -m pytest test_readings.py -v
```

Do **not** open `BUG.md` until after you’ve debugged.
