import os
import sys
import json
import subprocess
import urllib.request
from openai import OpenAI

def call_openrouter(system_prompt, user_prompt):
    client = OpenAI(
        base_url="https://openrouter.ai",
        api_key=os.getenv("OPENROUTER_API_KEY"),
        default_headers={
            "HTTP-Referer": "https://github.com", 
            "X-Title": "GitHub Actions Automation Bot"
        }
    )
    completion = client.chat.completions.create(
        model="deepseek/deepseek-chat",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    )
    return completion.choices.message.content

def post_github_comment(url, text):
    headers = {
        "Authorization": f"Bearer {os.getenv('GITHUB_TOKEN')}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "GitHub-Actions-AI-Bot"
    }
    data = json.dumps({"body": text}).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as response:
            if response.status in [200, 201]:
                print("Successfully posted message to GitHub.")
    except Exception as e:
        print(f"Error posting to GitHub: {e}")

def handle_pull_request(payload):
    print("Processing Pull Request Review...")
    base_branch = f"origin/{payload['pull_request']['base']['ref']}"
    try:
        pr_diff = subprocess.check_output(["git", "diff", f"{base_branch}...HEAD"], text=True)
    except Exception as e:
        print(f"Failed to get git diff: {e}")
        return
    if not pr_diff.strip():
        return
    sys_prompt = "You are an expert engineer. Review this code diff. Highlight bugs, security flaws, or bad logic. Keep it punchy."
    feedback = call_openrouter(sys_prompt, f"Review this diff:\n\n{pr_diff}")
    comments_url = payload["pull_request"]["comments_url"]
    post_github_comment(comments_url, f"🤖 **PR Code Review:**\n\n{feedback}")

def handle_issue(payload):
    print("Processing New Issue...")
    issue_title = payload["issue"]["title"]
    issue_body = payload["issue"]["body"] or "No description provided."
    sys_prompt = "You are a repository assistant. Analyze the issue reported by the user. Provide helpful debugging steps, clarify missing requirements, or offer a potential fix scenario."
    user_prompt = f"Issue Title: {issue_title}\nIssue Description:\n{issue_body}"
    answer = call_openrouter(sys_prompt, user_prompt)
    comments_url = payload["issue"]["comments_url"]
    post_github_comment(comments_url, f"🤖 **AI Issue Assistant:**\n\n{answer}")

def handle_comment(payload):
    comment_body = payload["comment"]["body"].strip()
    comments_url = payload["issue"]["comments_url"]
    if comment_body.startswith("/fix"):
        print("Processing code fix request...")
        code_to_fix = comment_body.replace("/fix", "").strip()
        if not code_to_fix:
            post_github_comment(comments_url, "❌ Please provide code context after the `/fix` command.")
            return
        sys_prompt = "You are a code generation machine. Refactor or fix the provided code snippet. Correct bugs, optimize efficiency, and output ONLY the corrected code wrapped in appropriate markdown blocks."
        fixed_code = call_openrouter(sys_prompt, code_to_fix)
        post_github_comment(comments_url, f"🤖 **AI Refactor Request:**\n\n{fixed_code}")
    elif "@ai-bot" in comment_body.lower():
        print("Processing direct bot mention...")
        sys_prompt = "You are an AI developer assistant maintaining this repository. Reply politely and helpfully to the team's questions."
        reply = call_openrouter(sys_prompt, comment_body)
        post_github_comment(comments_url, f"🤖 **AI Reply:**\n\n{reply}")

if __name__ == "__main__":
    event_name = os.getenv("GITHUB_EVENT_NAME")
    event_path = os.getenv("GITHUB_EVENT_PATH")
    with open(event_path, "r") as f:
        event_payload = json.load(f)
    if event_name == "pull_request":
        handle_pull_request(event_payload)
    elif event_name == "issues":
        handle_issue(event_payload)
    elif event_name == "issue_comment":
        handle_comment(event_payload)
