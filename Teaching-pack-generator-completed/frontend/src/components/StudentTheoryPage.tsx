import { useState, useEffect } from 'react';
import FlashcardView from './FlashcardView';

export default function StudentTheoryPage() {
  const [lessonId, setLessonId] = useState<number | null>(null);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const id = params.get('lessonId');
    if (id) {
      setLessonId(parseInt(id, 10));
    }
  }, []);

  if (!lessonId) {
    return <div className="flex items-center justify-center min-h-screen text-red-500">Invalid Lesson ID</div>;
  }

  return (
    <div className="min-h-screen bg-white">
      <FlashcardView 
        lessonId={lessonId} 
        onClose={() => window.close()} 
        isStandalone={true}
      />
    </div>
  );
}
