import React from 'react';

interface CoachingTipProps {
  tip: string;
  title?: string;
}

const CoachingTip: React.FC<CoachingTipProps> = ({ tip, title = "Coaching Tip" }) => {
  return (
    <div className="coaching-tip">
      <div className="coaching-tip-header">
        <span className="coaching-icon">💡</span>
        <h4>{title}</h4>
      </div>
      <p>{tip}</p>
    </div>
  );
};

export default CoachingTip;
