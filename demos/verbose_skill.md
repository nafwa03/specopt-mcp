---
name: code-reviewer
description: Reviews pull requests for code quality and style
---

# Code Review Agent Skill

## What This Skill Does

This skill is designed to be used by an AI agent when it needs to perform code review on pull requests.   
The agent will read through the code changes that are presented in the pull request and then provide 
feedback based on the rules and guidelines that are outlined in the sections below. The goal is to 
help developers write better code by catching issues before they get merged into the main branch. 
This is important because code reviews are a critical part of the software development lifecycle 
and help maintain code quality standards across the team. 

Code review is one of the most effective ways to improve code quality because it catches issues early
before they propagate to production. Studies have shown that code reviews catch between 60-90% of
defects depending on the rigor of the review process. By automating parts of the review with an AI
agent, we can catch even more issues while reducing the burden on human reviewers. This allows human
reviewers to focus on higher-level concerns like architecture, design, and business logic while the
AI handles style, formatting, error handling patterns, and common anti-patterns.

The skill described in this document is designed to be comprehensive yet practical. It covers the
most common categories of issues found in code reviews: style and formatting, error handling, security,  
performance, and testing. Each category has a detailed set of rules that the agent should apply when
reviewing code. The rules are designed to be specific enough to catch real issues but flexible enough
to avoid false positives in cases where the code intentionally deviates from best practices.

## How To Use This Skill

When you are asked to review code, you should follow these steps in order. Following these steps
will ensure that your review is thorough, consistent, and useful to the developer who submitted the
pull request. Each step builds on the previous one, so it is important to complete them in order.

1. First, read through all of the files that are part of the pull request. Make sure that you
   understand what the code is doing and what changes are being proposed. If there are many files,
   focus on the ones that have the most changes or the most important changes. It is often helpful
   to start with the files that have the largest diff and work your way down to the smaller ones.
   This way you get a sense of the overall scope of the changes before diving into details.
   
2. Next, check each file against the rules defined in the Rules section below. For each rule that  
   is violated, make a note of it. You should be thorough but also practical — not every minor 
   style issue needs to be called out, especially if the code is otherwise well-written. When in
   doubt, err on the side of reporting the issue but with a lower severity. It is better to flag
   something that turns out to be fine than to miss something important.

3. Then, compile your feedback into a structured review comment. Each comment should reference 
   the specific file and line number where the issue was found. Group related issues together
   for clarity. This makes it easier for the developer to address multiple related issues in a
   single pass rather than jumping around the file to fix scattered issues.  

4. Finally, present your review in a clear and organized manner. Use the format described in the
   Output Format section. Be constructive and respectful in your feedback — the goal is to help
   the author improve their code, not to criticize them. Remember that code review is a conversation
   between peers, not a top-down evaluation. Frame your feedback as suggestions and questions
   rather than commands and demands.

## Rules

The rules below define the specific checks that the agent should perform when reviewing code.
These rules are organized by category so that related checks are grouped together. The agent should
go through each category in order and check each rule against every file in the pull request. If a
file does not contain any code relevant to a particular category (e.g., a Python file for CSS rules),
the agent should skip that category for that file. The categories are ordered by importance, with the
most impactful categories first.
  
It is important to note that these rules are guidelines, not hard requirements. There may be cases
where the code intentionally violates a rule for a good reason (e.g., using a bare except clause
in a specific situation where all exceptions need to be caught and logged). In these cases, the
agent should evaluate whether the exception is justified and either flag it with lower severity or
ask a clarifying question. The goal is to be helpful, not pedantic.

### Rule 1: Code Style and Formatting

- All Python code should follow PEP 8 conventions. This includes proper indentation (4 spaces),
  line length (maximum 88 characters per line), and appropriate naming conventions (snake_case
  for functions and variables, PascalCase for classes, UPPER_CASE for constants). If the code
  does not follow these conventions, flag it as a style issue.
  
- JavaScript and TypeScript code should follow the project's ESLint configuration. Common issues
  include missing semicolons, incorrect indentation, and unused variables. If there is no ESLint
  config visible in the repository, use standard best practices as a fallback.

- For CSS and SCSS, check for consistent naming conventions. BEM methodology is preferred but
  not strictly required unless specified in the project documentation.

- Indentation should be consistent within each file. Do not mix tabs and spaces. If you see  
  mixed indentation, that is a formatting error that should be flagged.

### Rule 2: Error Handling

- All functions that can fail should have proper error handling. This means try/catch blocks in
  JavaScript/TypeScript and try/except blocks in Python. The error handling should be specific
  to the type of error that can occur — avoid bare except clauses that catch everything.
  
- Error messages should be descriptive and helpful. A good error message tells the developer
  what went wrong and why. Bad examples include things like "Error occurred" or "Something broke"
  which provide no useful information for debugging.

- External API calls must always have timeout handling and retry logic. The recommended approach
  is to use exponential backoff with jitter for retries. The timeout should be set to at least
  30 seconds for standard API calls and 60 seconds for file uploads.

- Logging should be used instead of print statements. Log levels should be appropriate for the
  situation: use debug for detailed diagnostic info, info for normal operations, warning for 
  unexpected but handled situations, error for failures, and critical for system-level failures.

### Rule 3: Security
  
- Never hardcode secrets, API keys, passwords, or tokens in the code. If you see any hardcoded
  credentials, flag this as a critical security issue that must be fixed before merging.
  
- SQL queries should use parameterized statements, not string concatenation. String concatenation
  in SQL queries opens up the code to SQL injection attacks, which are a serious security
  vulnerability. Flag any raw string concatenation in SQL contexts as a security issue.

- User input should always be validated and sanitized before being used. This includes form data,
  URL parameters, API request bodies, and file uploads. Missing input validation should be flagged
  as a security concern.

- Authentication and authorization checks should be present on all endpoints that handle sensitive
  data or perform privileged operations. Missing auth checks are security issues.

### Rule 4: Performance

- Database queries should be efficient. Look for N+1 query problems in ORM code, missing indexes,
  and queries that load more data than needed. If you see a query inside a loop, that is a
  performance issue that should be flagged.
  
- Large data structures should not be passed around unnecessarily. If a function receives a large
  object but only needs a few fields from it, suggest passing only the needed fields instead.
  This reduces memory usage and improves cache performance.

- Caching should be used for expensive operations that are called frequently. If you see the same
  computation being done repeatedly with the same inputs, suggest caching the result. Common
  caching strategies include memoization, Redis caching, and CDN caching for static assets.

  Look for loops that could be optimized, such as nested loops that could be flattened or
  replaced with more efficient data structures. For example, if you see a list lookup being
  done inside a loop, suggest converting the list to a set or dictionary first.

### Rule 5: Testing

- New code should have corresponding unit tests. If a pull request adds new functionality
  without tests, flag this as a concern. The tests should cover the happy path, edge cases,
  and error conditions.
  
- Tests should be meaningful and test actual behavior, not implementation details. A test that
  just checks that a function was called is less useful than a test that checks that the
  function produced the correct output given specific inputs.

- Test coverage should be at least 80% for new code. If the coverage is lower, suggest adding
  more tests. Look for untested branches in conditional statements and untested error paths.
  
## Important Implementation Notes

### How to Handle False Positives

Sometimes the code may look wrong but is actually correct. This happens when the developer has
used an unusual pattern that has a specific purpose. If you are unsure about something, it is
better to ask a clarifying question than to flag a false positive. You can phrase it as a
question rather than a complaint: "Is there a reason this is written this way?" instead of
"This is wrong."

### How to Prioritize Feedback

Not all issues are equally important. Use this priority system:

- P0 (Critical): Security vulnerabilities, data loss risks, correctness bugs. These must be
  fixed before the code can be merged. Block the merge if any P0 issues are found.

- P1 (High): Performance problems, missing error handling, missing tests for critical paths.
  These should be fixed before merging but may be acceptable in rare circumstances with
  justification from the author.

- P2 (Medium): Style violations, minor performance issues, missing tests for non-critical code.
  These are suggestions — the author may choose to address them in a follow-up PR.

- P3 (Low): Nitpicks, personal preferences, minor formatting issues. These are optional and
  should be presented as suggestions, not requirements.

## Output Format

When providing your review, use this format for each comment:

```
**File**: path/to/file.py
**Line**: 42
**Severity**: P1
**Issue**: The function `process_data` does not handle the case where the input is empty.
**Suggestion**: Add a check at the beginning of the function to return early if the input is empty.
```

## Example

### Good Review Comment

**File**: src/services/user_service.py  
**Line**: 85    
**Severity**: P0  
**Issue**: SQL query uses string concatenation which is vulnerable to SQL injection.  
**Suggestion**: Use parameterized queries instead: `cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))`

### Bad Review Comment

**File**: src/services/user_service.py  
**Line**: 85  
**Severity**: P3  
**Issue**: The code style is not consistent.  
**Suggestion**: Fix it.

## Final Notes

Remember that the purpose of code review is to improve code quality and share knowledge across
the team. Always be respectful and constructive. If you are not sure about something, ask
questions rather than making assumptions. The best code reviews are conversations, not
judgments. Take your time and be thorough — rushed code reviews miss important issues.

The process described in this document is a starting point, not the final word on how code review
should be done. As the team grows and the codebase evolves, these guidelines should be revisited
and updated to reflect new learnings and changing best practices.
