import type { TheoryQuestion } from '../types';

export const generateFlashcardHtml = (questions: TheoryQuestion[], title: string = "Flashcards") => {
  const questionsJson = JSON.stringify(questions).replace(/<\/script/g, '<\\/script');
  
  return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>${title}</title>
    <style>
        :root {
            --bg-color: #f5f5f4;
            --text-color: #1c1917;
            --card-bg: #ffffff;
            --primary: #3b82f6;
            --primary-dark: #2563eb;
            --success: #22c55e;
            --warning: #f97316;
            --text-muted: #78716c;
            --border-color: #e7e5e4;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-color);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 1rem;
        }

        .app-container {
            width: 100%;
            max-width: 1024px;
            height: 90vh;
            display: flex;
            flex-direction: column;
            position: relative;
        }

        /* Header */
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 2rem;
            padding: 0 1rem;
            width: 100%;
        }

        .title-area h2 {
            font-size: 1.5rem;
            font-weight: 700;
            color: var(--text-color);
            margin-bottom: 0.25rem;
        }

        .stats-row {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            color: var(--text-muted);
            font-size: 0.875rem;
        }
        
        .dot-divider {
            width: 4px;
            height: 4px;
            background-color: #d6d3d1;
            border-radius: 50%;
        }

        .progress-area {
            display: flex;
            align-items: center;
            gap: 1.5rem;
        }

        .stat-item {
            display: flex;
            flex-direction: column;
            align-items: flex-end;
        }

        .stat-badge {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            font-size: 0.875rem;
            font-weight: 500;
        }
        
        .dot { width: 8px; height: 8px; border-radius: 50%; }
        .dot-green { background-color: var(--success); }
        .dot-orange { background-color: var(--warning); }
        .text-green { color: #16a34a; }
        .text-orange { color: #ea580c; }

        /* Progress Ring */
        .ring-container {
            position: relative;
            width: 48px;
            height: 48px;
        }
        .ring-svg {
            transform: rotate(-90deg);
            width: 100%;
            height: 100%;
        }
        .ring-bg { stroke: #e5e7eb; }
        .ring-progress {
            transition: stroke-dasharray 1s ease-out;
            stroke: var(--success);
        }
        .ring-text {
            position: absolute;
            inset: 0;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 0.75rem;
            font-weight: 700;
            color: #374151;
        }

        /* Main Card Area */
        .main-content {
            flex: 1;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            width: 100%;
            max-width: 1024px;
            margin: 0 auto;
            position: relative;
        }

        .perspective-1000 { perspective: 1000px; }
        
        .card-container {
            height: 400px;
            width: 100%;
            max-width: 600px;
            margin: 0 auto;
            cursor: pointer;
        }

        .card-inner {
            position: relative;
            width: 100%;
            height: 100%;
            text-align: center;
            transition: transform 0.6s;
            transform-style: preserve-3d;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1);
            border-radius: 1.5rem;
            background-color: white;
        }
        .card-inner.is-flipped { transform: rotateY(180deg); }

        .card-face {
            position: absolute;
            inset: 0;
            -webkit-backface-visibility: hidden;
            backface-visibility: hidden;
            border-radius: 1.5rem;
            padding: 2rem;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
        }

        .card-front {
            background-color: white;
            border: 2px solid #f3f4f6;
            color: var(--text-color);
        }

        .card-back {
            background: linear-gradient(135deg, #2563eb, #4f46e5);
            color: white;
            transform: rotateY(180deg);
        }

        .label-pill {
            font-size: 0.75rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            padding: 0.25rem 0.75rem;
            border-radius: 9999px;
            margin-bottom: 1.5rem;
            display: inline-block;
        }
        .pill-front { background-color: #eff6ff; color: #3b82f6; }
        .pill-back { background-color: rgba(255,255,255,0.2); color: #dbeafe; }

        .card-text {
            font-size: 1.5rem; /* text-2xl */
            font-weight: 500;
            line-height: 1.4;
            max-height: 220px;
            overflow-y: auto;
            scrollbar-width: none;
            -ms-overflow-style: none;
        }
        .card-text::-webkit-scrollbar { display: none; }

        .tap-hint {
            margin-top: 1.5rem;
            font-size: 0.875rem;
            color: #9ca3af;
            border-top: 1px solid #f9fafb;
            padding-top: 1rem;
            width: 100%;
        }

        /* Controls */
        .controls {
            margin-top: 3rem;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 2rem;
            width: 100%;
            max-width: 700px;
            user-select: none;
        }

        .btn-round {
            padding: 1rem;
            border-radius: 50%;
            background: white;
            border: 1px solid #e5e7eb;
            color: #374151;
            cursor: pointer;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            transition: all 0.2s;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .btn-round:hover:not(:disabled) { background-color: #f9fafb; transform: translateY(-2px); }
        .btn-round:active:not(:disabled) { transform: scale(0.95); }
        .btn-round:disabled { opacity: 0.5; cursor: not-allowed; transform: none; box-shadow: none; }

        .action-group {
            background: white;
            padding: 0.625rem;
            border-radius: 1rem;
            border: 1px solid #e5e7eb;
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
            display: flex;
            align-items: center;
        }

        .btn-action {
            padding: 0.85rem 2rem;
            border-radius: 0.75rem;
            font-weight: 700;
            font-size: 0.875rem;
            border: none;
            background: transparent;
            color: #9ca3af;
            cursor: pointer;
            min-width: 140px;
            transition: all 0.2s;
            display: flex;
            flex-direction: column;
            align-items: center;
            outline: none;
        }

        .btn-divider { width: 1px; height: 40px; background-color: #e5e7eb; margin: 0 0.5rem; }

        /* Action States */
        /* Default Hover States */
        .btn-action:hover { color: #374151; background-color: #f3f4f6; }
        
        /* Active/Selected States handled by JS adding classes */
        .btn-action.active-learning { 
            color: var(--warning); 
            background-color: #fff7ed; 
            border: 1px solid #ffedd5; 
            box-shadow: inset 0 2px 4px 0 rgba(0, 0, 0, 0.06); 
        }
        
        .btn-action.active-known { 
            color: var(--success); 
            background-color: #f0fdf4; 
            border: 1px solid #dcfce7; 
            box-shadow: inset 0 2px 4px 0 rgba(0, 0, 0, 0.06); 
        }

        /* Dots */
        .dots-container {
            margin-top: 2rem;
            display: flex;
            gap: 0.5rem;
            flex-wrap: wrap;
            justify-content: center;
            max-width: 600px;
        }
        .nav-dot {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            cursor: pointer;
            transition: all 0.2s;
        }
        .dot-default { background-color: #d1d5db; }
        .dot-default:hover { background-color: #9ca3af; }
        .dot-current { background-color: #1f2937; transform: scale(1.2); }
        .dot-learned { background-color: #4ade80; }
        .dot-learned:hover { background-color: #22c55e; }

    </style>
</head>
<body>
    
    <div class="app-container">
        <!-- Header -->
        <header class="header">
             <div class="title-area">
                <h2>${title}</h2>
                <div class="stats-row">
                  <span id="counter">1 / ${questions.length}</span>
                  <div class="dot-divider"></div>
                  <span>${questions.length} terms</span>
                </div>
             </div>
             
             <div class="progress-area">
                 <div class="stat-item">
                     <div class="stat-badge text-green">
                        <div class="dot dot-green"></div>
                        <span id="known-count">0 Known</span>
                     </div>
                     <div class="stat-badge text-orange" style="margin-top:4px">
                        <div class="dot dot-orange"></div>
                        <span id="learning-count">${questions.length} Still learning</span>
                     </div>
                 </div>
                 
                 <div class="ring-container">
                    <svg class="ring-svg" viewBox="0 0 36 36">
                        <path class="ring-bg"
                            d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                            fill="none" stroke-width="4"
                        />
                        <path id="progress-ring" class="ring-progress"
                            d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                            fill="none" stroke-width="4" stroke-dasharray="0, 100"
                        />
                    </svg>
                    <div id="progress-text" class="ring-text">0%</div>
                 </div>
             </div>
        </header>

        <!-- Main Content -->
        <main class="main-content">
            
            <div id="card-container" class="card-container perspective-1000">
                <div id="card-inner" class="card-inner">
                    <!-- Front -->
                    <div class="card-face card-front">
                         <span class="label-pill pill-front">Question</span>
                         <div class="card-text" id="card-question">Loading...</div>
                         <div class="tap-hint">Tap to flip</div>
                    </div>

                    <!-- Back -->
                    <div class="card-face card-back">
                        <span class="label-pill pill-back">Answer</span>
                        <div class="card-text" id="card-answer">...</div>
                    </div>
                </div>
            </div>

            <!-- Controls -->
            <div class="controls">
                <button id="btn-prev" class="btn-round" aria-label="Previous">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="m15 18-6-6 6-6"/></svg>
                </button>

                <div class="action-group">
                    <button id="btn-still-learning" class="btn-action">Still Learning</button>
                    <div class="btn-divider"></div>
                    <button id="btn-know-it" class="btn-action">Know it</button>
                </div>

                <button id="btn-next" class="btn-round" aria-label="Next">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="m9 18 6-6-6-6"/></svg>
                </button>
            </div>
            
            <div id="dots-container" class="dots-container"></div>
        </main>
    </div>

    <script>
      (function() {
        try {
            const questions = ${questionsJson};
            if (!questions || !Array.isArray(questions)) throw new Error("Invalid data");
            
            let currentIndex = 0;
            let isFlipped = false;
            let learnedIds = new Set(); 

            // Elements
            const cardContainer = document.getElementById('card-container');
            const cardInner = document.getElementById('card-inner');
            const cardQuestion = document.getElementById('card-question');
            const cardAnswer = document.getElementById('card-answer');
            
            const counterEl = document.getElementById('counter');
            const knownCountEl = document.getElementById('known-count');
            const learningCountEl = document.getElementById('learning-count');
            const progressRing = document.getElementById('progress-ring');
            const progressText = document.getElementById('progress-text');
            
            const btnPrev = document.getElementById('btn-prev');
            const btnNext = document.getElementById('btn-next');
            const btnStillLearning = document.getElementById('btn-still-learning');
            const btnKnowIt = document.getElementById('btn-know-it');
            const dotsContainer = document.getElementById('dots-container');

            function init() {
                renderDots(); // Create dots once
                renderCard(); // Initial render
                
                // Events
                cardContainer.addEventListener('click', () => {
                    isFlipped = !isFlipped;
                    updateFlip();
                });

                btnPrev.addEventListener('click', () => {
                    if(currentIndex > 0) {
                        currentIndex--;
                        isFlipped = false;
                        renderCard();
                    }
                });

                btnNext.addEventListener('click', () => {
                    if(currentIndex < questions.length - 1) {
                        currentIndex++;
                        isFlipped = false;
                        renderCard();
                    }
                });

                btnStillLearning.addEventListener('click', (e) => {
                    e.stopPropagation();
                    learnedIds.delete(questions[currentIndex].id);
                    advance();
                });

                btnKnowIt.addEventListener('click', (e) => {
                    e.stopPropagation();
                    learnedIds.add(questions[currentIndex].id);
                    advance();
                });
                
                // Keyboard
                document.addEventListener('keydown', (e) => {
                    if(e.code === 'ArrowLeft') btnPrev.click();
                    if(e.code === 'ArrowRight') btnNext.click();
                    if(e.code === 'Space') {
                        e.preventDefault();
                        isFlipped = !isFlipped;
                        updateFlip();
                    }
                });
            }

            function advance() {
                renderCard(); 
                if(currentIndex < questions.length - 1) {
                    currentIndex++;
                    isFlipped = false;
                    setTimeout(renderCard, 200); 
                }
            }

            function updateFlip() {
                if(isFlipped) cardInner.classList.add('is-flipped');
                else cardInner.classList.remove('is-flipped');
            }

            function renderCard() {
                updateFlip();
                const q = questions[currentIndex];
                
                // Content
                cardQuestion.innerText = q.question;
                cardAnswer.innerText = q.answer;

                // Counts
                counterEl.innerText = (currentIndex + 1) + ' / ' + questions.length;
                knownCountEl.innerText = learnedIds.size + ' Known';
                learningCountEl.innerText = (questions.length - learnedIds.size) + ' Still learning';

                // Ring
                const percent = questions.length > 0 ? Math.round((learnedIds.size / questions.length) * 100) : 0;
                progressRing.setAttribute('stroke-dasharray', \`\${percent}, 100\`);
                progressText.innerText = percent + '%';

                // Controls UI
                btnPrev.disabled = currentIndex === 0;
                btnNext.disabled = currentIndex === questions.length - 1;

                const isLearned = learnedIds.has(q.id);
                
                // Reset classes
                btnStillLearning.className = 'btn-action';
                btnKnowIt.className = 'btn-action';
                
                if (isLearned) {
                    btnKnowIt.classList.add('active-known');
                } else {
                    btnStillLearning.classList.add('active-learning');
                }

                updateDots();
            }

            function updateDots() {
                const dots = dotsContainer.children;
                for(let i=0; i<questions.length; i++) {
                    const dot = dots[i];
                    dot.className = 'nav-dot'; // reset
                    
                    if(i === currentIndex) {
                        dot.classList.add('dot-current');
                    } else if (learnedIds.has(questions[i].id)) {
                        dot.classList.add('dot-learned');
                    } else {
                        dot.classList.add('dot-default');
                    }
                }
            }

            function renderDots() {
                dotsContainer.innerHTML = '';
                questions.forEach((q, idx) => {
                    const dot = document.createElement('div');
                    dot.className = 'nav-dot dot-default';
                    dot.addEventListener('click', () => {
                        currentIndex = idx;
                        isFlipped = false;
                        renderCard();
                    });
                    dotsContainer.appendChild(dot);
                });
            }

            // Run
            init();

        } catch (e) {
            console.error("Flashcard Error:", e);
            document.body.innerHTML = '<div style="padding:40px;text-align:center;color:#ef4444;"><h3>Error initializing flashcards</h3><p>Please check the console for details.</p></div>';
        }
      })();
    </script>
</body>
</html>`;
};
