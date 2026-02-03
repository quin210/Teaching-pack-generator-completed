import { useState } from 'react';

interface UploadAreaProps {
  fileName: string;
  studentListFileName?: string;
  onFileChange: (file: File | null) => void;
  onStudentListFileChange?: (file: File | null) => void;
}

export default function UploadArea({ fileName, studentListFileName, onFileChange, onStudentListFileChange }: UploadAreaProps) {
  const [isDragOver, setIsDragOver] = useState(false);

  const handleClick = (inputId: string = 'fileInput') => {
    const input = document.getElementById(inputId) as HTMLInputElement;
    input?.click();
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDragEnter = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent, callback: (file: File | null) => void) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);

    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      const file = files[0];
      // Check file types broadly for now, specific logic can be added if needed
      callback(file);
    }
  };

  return (
    <div className="flex gap-4">
      {/* Lesson File Upload */}
      <div 
        onClick={() => handleClick('fileInput')}
        onDragOver={handleDragOver}
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDrop={(e) => handleDrop(e, onFileChange)}
        className={`flex-1 group relative overflow-hidden rounded-2xl border-2 border-dashed p-6 text-center cursor-pointer transition-all duration-300 ${
          fileName ? 'border-green-300 bg-green-50/50' : 
          isDragOver ? 'border-yellow-400 bg-yellow-50' : 
          'border-black/10 hover:border-yellow-400 hover:bg-yellow-50/30 bg-white/50'
        }`}
      >
        <input 
          id="fileInput"
          type="file" 
          onChange={(e) => onFileChange(e.target.files?.[0] || null)}
          className="hidden" 
          accept=".pdf,.jpg,.jpeg,.png,image/*" 
        />
        
        <div className="relative z-10 flex flex-col items-center gap-2">
          {fileName ? (
            <>
              <div className="w-10 h-10 rounded-full bg-green-100 text-green-600 flex items-center justify-center font-bold text-lg">?</div>
              <p className="font-semibold text-green-700 text-sm">File selected</p>
              <p className="text-green-600 text-xs truncate max-w-[200px]" title={fileName}>{fileName}</p>
            </>
          ) : (
            <>
              <div className="w-12 h-12 rounded-2xl bg-white border border-black/5 flex items-center justify-center text-2xl shadow-md">
                📄
              </div>
              <p className="font-semibold text-zinc-700 text-sm">Upload lesson (PDF/Image)</p>
              <p className="text-zinc-500 text-xs">Drag & drop or click to select</p>
            </>
          )}
        </div>
      </div>
      {onStudentListFileChange && (
        <div
          onClick={() => handleClick('studentFileInput')}
          onDragOver={handleDragOver}
          onDragEnter={handleDragEnter}
          onDragLeave={handleDragLeave}
          onDrop={(e) => handleDrop(e, onStudentListFileChange)}
          className={`flex-1 group relative overflow-hidden rounded-2xl border-2 border-dashed p-6 text-center cursor-pointer transition-all duration-300 ${
            studentListFileName ? 'border-green-300 bg-green-50/50' :
            isDragOver ? 'border-yellow-400 bg-yellow-50' :
            'border-black/10 hover:border-yellow-400 hover:bg-yellow-50/30 bg-white/50'
          }`}
        >
          <input
            id="studentFileInput"
            type="file"
            onChange={(e) => onStudentListFileChange(e.target.files?.[0] || null)}
            className="hidden"
            accept=".csv,.xlsx,.txt"
          />

          <div className="relative z-10 flex flex-col items-center gap-2">
            {studentListFileName ? (
              <>
                <div className="w-10 h-10 rounded-full bg-green-100 text-green-600 flex items-center justify-center font-bold text-lg">?</div>
                <p className="font-semibold text-green-700 text-sm">File selected</p>
                <p className="text-green-600 text-xs truncate max-w-[200px]" title={studentListFileName}>{studentListFileName}</p>
              </>
            ) : (
              <>
                <div className="w-12 h-12 rounded-2xl bg-white border border-black/5 flex items-center justify-center text-2xl shadow-md">
                  dY"?
                </div>
                <p className="font-semibold text-zinc-700 text-sm">Upload lesson (PDF/Image)</p>
                <p className="text-zinc-500 text-xs">CSV/XLSX/TXT</p>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}