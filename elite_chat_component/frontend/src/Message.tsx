import React from 'react';
import ReactMarkdown from 'react-markdown';
import CoachingTip from './CoachingTip';

interface MessageProps {
  role: 'user' | 'assistant';
  content: string;
  hasCoaching?: boolean;
  coachingTip?: string;
  rolePlayLevel?: number;
}

// Function to extract coaching tip from message content if present
const extractCoachingTip = (content: string): { tip: string | null, cleanContent: string } => {
  const coachingRegex = /^COACHING_TIP:([\s\S]+?)END_COACHING_TIP/;
  const match = content.match(coachingRegex);
  
  if (match) {
    return {
      tip: match[1].trim(),
      cleanContent: content.replace(coachingRegex, '').trim()
    };
  }
  
  return {
    tip: null,
    cleanContent: content
  };
};

// Function to extract role-play level from message content if present
const extractRolePlayLevel = (content: string): { level: number | null, cleanContent: string } => {
  const levelRegex = /^ROLE_PLAY_LEVEL:(\d+)END_ROLE_PLAY_LEVEL/;
  const match = content.match(levelRegex);
  
  if (match) {
    return {
      level: parseInt(match[1]),
      cleanContent: content.replace(levelRegex, '').trim()
    };
  }
  
  return {
    level: null,
    cleanContent: content
  };
};

const Message: React.FC<MessageProps> = ({ role, content, hasCoaching, coachingTip, rolePlayLevel }) => {
  // Process content to extract coaching tips and role-play levels if they exist
  const { tip: extractedTip, cleanContent: contentWithoutTip } = extractCoachingTip(content);
  const { level: extractedLevel, cleanContent: finalContent } = extractRolePlayLevel(contentWithoutTip);
  
  // Use either passed props or extracted values
  const finalCoachingTip = coachingTip || extractedTip;
  const finalRolePlayLevel = rolePlayLevel || extractedLevel;

  return (
    <div className={`message ${role}`}>
      {finalCoachingTip && (
        <CoachingTip tip={finalCoachingTip} />
      )}
      
      {finalRolePlayLevel && (
        <div className="role-play-level">
          Role-Play Depth: Level {finalRolePlayLevel}
        </div>
      )}
      
      {role === 'assistant' ? (
        <div className="markdown-content">
          <ReactMarkdown>{finalContent}</ReactMarkdown>
        </div>
      ) : (
        <p>{finalContent}</p>
      )}
    </div>
  );
};

export default Message;
