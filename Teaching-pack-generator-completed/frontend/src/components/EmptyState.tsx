export default function EmptyState() {
  return (
    <div className="text-center py-20 px-5">
      <div className="w-20 h-20 mx-auto mb-4 rounded-full bg-stone-100 flex items-center justify-center">
        <div className="w-12 h-12 border-4 border-stone-300 rounded-lg" />
      </div>
      <p className="text-stone-500 text-lg">Upload a lesson and enter class info to get started</p>
    </div>
  );
}
