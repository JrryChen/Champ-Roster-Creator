# Championship Analysis Tool

Automated tool to analyze swimmers' times against ACC and NCAA championship standards.

## 🎯 What This Tool Does

This tool automatically:

1. **Scrapes** swimmer IDs and names from your team roster
2. **Collects** individual event data for each swimmer
3. **Fetches** championship finals times (ACC & NCAA)
4. **Analyzes** how your swimmers compare to championship standards
5. **Generates** Excel-ready CSV files with time comparisons

## 📊 Output Files

The tool creates two main CSV files:

### `swimmer_championship_comparison_acc.csv`

- Compares swimmers to ACC Championship finals times
- Shows time drops needed to reach 1st, 3rd, 8th, 16th, and 24th place
- Includes both best times and season best times

### `swimmer_championship_comparison_ncaa.csv`

- Compares swimmers to NCAA Championship finals times
- Only includes swimmers who meet NCAA invite standards
- Shows time drops needed for finals placements

## 🚀 Quick Start (For Non-Technical Users)

### Option 1: Interactive Mode (Easiest)

```bash
python analyze_team.py
```

Just follow the prompts! The tool will ask you:

- Your team's SwimCloud ID
- Which gender(s) to analyze

### Option 2: Command Line

```bash
# Analyze both men and women
python championship_workflow.py --team 405

# Analyze only women
python championship_workflow.py --team 405 --gender women

# Analyze only men
python championship_workflow.py --team 405 --gender men
```

## 📋 Requirements

### Python Packages

Install required packages:

```bash
pip install requests beautifulsoup4 httpx
```

Or use the requirements file:

```bash
pip install -r requirements.txt
```

### Finding Your Team ID

1. Go to SwimCloud.com
2. Find your team's page
3. Look at the URL: `https://www.swimcloud.com/team/405/`
4. The number (405 in this example) is your team ID

## 📁 Generated Files

After running, you'll have:

```
├── M_swimmers.csv                              # Men's swimmer list
├── F_swimmers.csv                              # Women's swimmer list
├── M_Events/                                   # Men's event data
│   ├── all_M_Events.json
│   └── [individual swimmer files]
├── F_Events/                                   # Women's event data
│   ├── all_F_Events.json
│   └── [individual swimmer files]
├── acc_2025_finals_times.json                  # ACC standards
├── M_ncaa_2025_finals_times.json              # NCAA Men's standards
├── W_ncaa_2025_finals_times.json              # NCAA Women's standards
├── swimmer_championship_comparison_acc.csv     # 📊 MAIN OUTPUT
└── swimmer_championship_comparison_ncaa.csv    # 📊 MAIN OUTPUT
```

## 📖 Understanding the Output

### CSV Column Headers

- **swimmer_name**: Swimmer's full name
- **swimmer_id**: SwimCloud ID
- **event**: Event name (e.g., "100 Free")
- **best_time**: Personal best time
- **season_best**: Best time this season
- **time_drop_to_1**: Seconds to drop to beat 1st place time (0 if already faster)
- **time_drop_to_3**: Seconds to drop to beat 3rd place time
- **time_drop_to_8**: Seconds to drop to beat 8th place time
- **time_drop_to_16**: Seconds to drop to beat 16th place time (ACC only)
- **time_drop_to_24**: Seconds to drop to beat 24th place time (ACC only)

### Interpreting Results

- **0** in a time_drop column = Swimmer is already faster than that placement
- **Positive number** = Seconds swimmer needs to drop to reach that placement
- **N/A** for season_best = No swims recorded this season yet

## 🔧 Advanced Usage

### Run Individual Steps

If you need to run steps separately:

```bash
# Step 1: Get swimmer IDs
python scrape_swim_ids.py women

# Step 2: Get swimmer events
python scrape_events.py F

# Step 3: Get championship times
python scrape_finals_times.py 307261 42 acc

# Step 4: Run analysis
python champ_roster_enhanced.py women
```

### Championship Meet IDs

Current meet IDs in the system:

- **ACC 2025**: 307261 (42 events)
- **NCAA Men's 2025**: 296883 (21 events)
- **NCAA Women's 2025**: 296884 (21 events)

To update for future years, find the meet ID in the SwimCloud URL.

## ⚙️ Configuration

### Rate Limiting

The tool includes automatic rate limiting to avoid being blocked by SwimCloud:

- 3 seconds between swimmers
- 2 seconds between events
- 10 second pause every 5 swimmers
- Automatic retry with exponential backoff on rate limit errors

### NCAA Invite Standards

NCAA invite times are defined in `ncaa_invite_times.py`. Update this file to use different invite standards.

## 🐛 Troubleshooting

### "Rate Limited" Errors

The tool handles rate limiting automatically with retries. If you continue to see errors:

- Wait a few minutes before running again
- Reduce the number of swimmers being processed

### "No swimmers found"

- Verify your team ID is correct
- Check that the team has a public roster on SwimCloud
- Ensure you're using the current season (season_id=29)

### Missing Output Files

- Check for error messages in the console output
- Ensure all required Python packages are installed
- Verify internet connection

## 📝 File Descriptions

### Core Scripts

- `analyze_team.py` - Simple interactive interface
- `championship_workflow.py` - Main automation workflow
- `champ_roster_enhanced.py` - Analysis engine with rate limiting
- `scrape_swim_ids.py` - Scrapes team roster
- `scrape_events.py` - Scrapes swimmer events
- `scrape_finals_times.py` - Scrapes championship times

### Configuration Files

- `ncaa_invite_times.py` - NCAA invite time standards
- `event_dictionary.py` - Event name mappings

### Supporting Files

- `SwimScrape/` - SwimCloud API client library

## 🎓 For Coaches

This tool is designed to help you:

1. **Identify** which swimmers are close to championship qualifying times
2. **Plan** training focus based on time drops needed
3. **Track** progress throughout the season
4. **Make** informed roster decisions for championship meets

## 📞 Support

If you encounter issues:

1. Check the troubleshooting section above
2. Review console output for specific error messages
3. Ensure all prerequisites are installed
4. Verify your team ID and gender settings

## 🔄 Updating Data

To refresh with the latest data:

1. Delete existing CSV and JSON files
2. Re-run the workflow
3. The tool will scrape fresh data from SwimCloud

## ⚡ Performance Notes

- Full workflow takes approximately 5-10 minutes per gender
- Time depends on roster size and SwimCloud response times
- Progress is saved incrementally to protect against interruptions

## 📜 License

This tool is for educational and coaching purposes. Please respect SwimCloud's terms of service and rate limits.

---

**Questions?** Review the code comments or check the console output for detailed progress information.
