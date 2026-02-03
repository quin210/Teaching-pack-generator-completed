// Type for specific group in GroupsData
export interface GroupProfile {
  group_name: string;
  description: string;
  mastery_level: string;
  learning_style: string;
  rationale: string;
}

export interface GroupOverview {
  group_id: string;
  students: string[];
  profile: GroupProfile;
  // Adding optional fields to match potential backend response if they exist, or remove usage if they don't
  // Assuming 'level', 'avg_score', 'diversity' etc are NOT in profile based on user feedback
}

export interface GroupsData {
  groups: Record<string, GroupOverview>;
  num_groups: number;
  num_students: number;
}
