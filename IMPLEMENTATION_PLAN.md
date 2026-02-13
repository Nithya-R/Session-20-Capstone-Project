# Civic Lens - Implementation Plan

## Goal Description
Build "Civic Lens", an **Adaptive Learning Platform** for Indian Politics.
The system will feature:
1.  **Knowledge Repo (Admin)**: To ingest content and tag it by complexity (Levels 1-15).
2.  **Assessment Engine**: To determine a user's baseline knowledge via a multi-level quiz.
3.  **Continuous Learning**: A personalized journey that serves bite-sized lessons based on the user's current level and weak areas.

## User Review Required
> [!IMPORTANT]
> **LLM Integration**: The app will require a **Google Gemini API Key** (or similar) to function fully.
> - **Tagging**: The app will send content to the LLM with the `TaggingCriteria` system prompt to auto-assign levels/topics.
> - **Questions**: The app will generate questions dynamically using the LLM.
> - **Fallback**: I will still include a `default_questions.json` file as requested, to ensure the app works immediately even without a key.

> [!NOTE]
> **Data Persistence**: I will use **LocalStorage** to save the User's Progress and Knowledge Repo additions so the app feels "stateful" during the demo.

## Proposed Changes

### Core Architecture
#### [NEW] [LLM Service]
- `src/services/ai_service.ts`: Handles API calls to Gemini/OpenAI.
- `src/hooks/useAI`: Hook to expose AI capabilities to components.

#### [NEW] [Store/Context]
- `useUserStore`: Tracks Current Level, XP, History, and **In Progress** topics (formerly Weak Areas).
- `useContentStore`: Acts as the Knowledge Repo (Content + Tags + Levels).

### Key Features

#### [NEW] [AdminDashboard.tsx](file:///c:/Users/Nithya/My%20Project%20-%20EAG/src/components/Admin/AdminDashboard.tsx)
- Interface to input text/links.
- **Auto-Tagger**: Button to "Analyze with AI" -> returns Level & Tags.

#### [NEW] [TaggingCriteria.ts](file:///c:/Users/Nithya/My%20Project%20-%20EAG/src/data/TaggingCriteria.ts)
- **Rules Engine**: Encodes the user-provided criteria as a **System Prompt** for the LLM.
- **Topic Taxonomy**: Defines the list of high-level topics.

#### [NEW] [AssessmentFlow.tsx](file:///c:/Users/Nithya/My%20Project%20-%20EAG/src/components/Assessment/AssessmentFlow.tsx)
- The initial "Calibration Test".
- Logic: Tries to generate fresh questions via LLM.
- **Fallback**: Uses `default_questions.json` if API fails or key is missing.

#### [NEW] [LearningJourney.tsx](file:///c:/Users/Nithya/My%20Project%20-%20EAG/src/components/Journey/LearningJourney.tsx)
- The main user view.
- Visual "Path" or "Map" of progress.
- "Start Next Lesson" button that fetches content appropriately challenging (Current Level + 1).

### content/
#### [NEW] [mock_curriculum.ts](file:///c:/Users/Nithya/My%20Project%20-%20EAG/src/data/mock_curriculum.ts)
- A robust dataset of Indian Political facts/concepts mapped to levels.
- *Examples*:
    - **Lvl 1**: "Who is the Prime Minister?"
    - **Lvl 8**: "Powers of the Rajya Sabha vs Lok Sabha."
    - **Lvl 15**: "Constitutional Amendment Procedures (Art 368)."

## Verification Plan

### Automated Tests
- Unit tests for the "Level Estimation" algorithm (e.g., if user answers L1-L5 correctly but fails L6, set Level to 5).

### Manual Verification
- **Admin Flow**: Add a new topic, see it appear in the repo.
- **Assessment**: Complete the quiz as a "Beginner" and verify the system starts me at Level 1.
- **Assessment**: Complete the quiz as an "Expert" and verify the system starts me at Level 10+.
- **Journey**: Verify the "Next Lesson" serves content matching the calculated level.
