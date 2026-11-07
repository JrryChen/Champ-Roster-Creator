# Quick Reference Guide

## 🚀 Getting Started in 3 Steps

### Step 1: Install Python

If you don't have Python installed:

- Download from [python.org](https://www.python.org/downloads/)
- During installation, check "Add Python to PATH"

### Step 2: Install Requirements

Open terminal/command prompt in this folder and run:

```bash
pip install -r requirements.txt
```

### Step 3: Run the Tool

**Option A - Interactive (Easiest):**

- Windows: Double-click `START_HERE.bat`
- Mac/Linux: Run `python analyze_team.py`

**Option B - Command Line:**

```bash
python championship_workflow.py --team 405 --gender women
```

---

## 📊 Quick Commands

### Analyze Specific Team

```bash
# Replace 405 with your team's ID
python championship_workflow.py --team 405 --gender women
```

### Find Your Team ID

1. Go to SwimCloud.com
2. Search for your team
3. Look at URL: `swimcloud.com/team/[ID]`
4. Use that number

### Common Team IDs

- Pittsburgh: 405
- Virginia: 401
- North Carolina: 394
- NC State: 395
- Duke: 390

---

## 📁 Output Files

After running, open these files in Excel:

- `swimmer_championship_comparison_acc.csv` - ACC comparison
- `swimmer_championship_comparison_ncaa.csv` - NCAA comparison

---

## 🔄 Re-run Analysis

To get fresh data:

1. Delete old CSV files
2. Run the tool again
3. New data will be scraped

---

## ⚡ Quick Tips

### Speed Up Analysis

- Analyze one gender at a time
- The tool saves progress automatically
- If interrupted, you can resume

### Understanding Output

- **0** = Already faster than that place
- **Number** = Seconds to drop
- **N/A** = No season time yet

### Troubleshooting

- "Rate Limited" - Wait 5 minutes, try again
- "No swimmers found" - Check team ID
- "Connection error" - Check internet

---

## 📞 Need Help?

1. Read error message in console
2. Check README.md for detailed info
3. Verify team ID and gender are correct
4. Make sure internet is working

---

## 🎯 Use Cases

### For Coaches

- Identify swimmers close to qualifying
- Set realistic time goals
- Make championship roster decisions
- Track progress throughout season

### For Swimmers

- See personal improvement needed
- Compare to championship standards
- Set training goals
- Visualize progress

---

## 📅 Season Updates

Update these files for new season:

- `ncaa_invite_times.py` - NCAA invite standards
- `championship_workflow.py` - Meet IDs (lines 115-137)

Find new meet IDs at SwimCloud after championship meets.

---

**Last Updated:** December 2025  
**Current Season:** 2024-2025 (Season 29)
