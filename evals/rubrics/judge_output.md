Write your verdict as JSON to the path you are given, with exactly this shape, then reply with a 5-line summary:

{
  "judge": "<your name>",
  "pages": {
    "<page-viewport>": {
      "scores": {"hierarchy": 0, "clarity": 0, "density": 0, "consistency": 0, "mobile": 0, "polish": 0, "game-feel": 0, "copy": 0},
      "problems": [{"severity": "high|medium|low", "where": "", "problem": "", "fix": ""}]
    }
  },
  "top_fixes": ["the five changes that would raise the scores most, most valuable first"]
}
