interface LoadingProps {
  message?: string;
}

export default function Loading({ message = 'Analyzing lesson and generating groups...' }: LoadingProps) {
  return (
    <div className="text-center py-12">
      <div className="w-12 h-12 border-4 border-yellow-500/20 border-t-yellow-500 rounded-full animate-spin mx-auto mb-5" />
      <p className="text-stone-600">{message}</p>
    </div>
  );
}
