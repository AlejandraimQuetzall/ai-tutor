export type ShelfItem = {
  id: string;
  name: string;
  kind: string;
  created_at?: string;
};

export type CourseSummary = {
  id: string;
  title: string;
  status: string;
  progress: number;
  sample: number | boolean;
  updated_at: string;
};

export type Citation = {
  quote: string;
  source_name: string;
  locator: string;
};

export type QuizOption = { id: string; text: string };

export type Question = {
  stem: string;
  options: QuizOption[];
  hint: string;
  answered: boolean;
  choice: string;
  correct: boolean;
  correct_id: string;
  explanation: string;
  quote: string;
  source_name: string;
  locator: string;
};

export type Chapter = {
  id: string;
  position: number;
  title: string;
  overview: string;
  lesson_md: string;
  summary_md: string;
  citations: Citation[];
  questions: Question[];
  opened: boolean;
  quiz_correct: boolean;
  quiz_answered: boolean;
  note: string;
  unlocked: boolean;
};

export type Course = {
  id: string;
  title: string;
  goal: string;
  depth: string;
  status: string;
  stage: string;
  message: string;
  progress: number;
  warning: string;
  overview: string;
  sample: boolean;
  materials: { id: string; name: string; kind: string }[];
  chapters: Chapter[];
  studied: number;
  chapter_count: number;
};

export const PRODUCT_URL =
  "https://lynote.ai/learning-path?utm_source=github&utm_medium=app&utm_campaign=learning_path_oss";

export const HOME_URL =
  "https://lynote.ai/?utm_source=github&utm_medium=app&utm_campaign=learning_path_oss";
