export default function Header() {
  return (
    <header className="relative overflow-hidden bg-linear-to-r from-yellow-100 via-yellow-200 to-yellow-400 text-yellow-900 p-10 mb-8 rounded-3xl border border-yellow-300/10">
      <div className="absolute -top-1/2 -right-[10%] w-75 h-75 rounded-full bg-gradient-radial from-yellow-400/30 to-transparent animate-float" />
      <h1 className="relative z-10 text-3xl font-semibold mb-2 tracking-tight">Teaching Pack Generator</h1>
      <p className="relative z-10 opacity-85 text-[15px]">Adaptive Grouping by Lesson & Content Generation</p>
    </header>
  );
}
