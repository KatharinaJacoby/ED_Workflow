# Revised Abstract

**From Curiosity to Code: A Clinician's Learning Journey in Healthcare AI**

**Author:** Dr. med. Katharina Jacoby  
**Word count:** ~250

**Background**
While healthcare AI often requires large teams and professional engineering expertise, we wondered: can a single clinician learn to build meaningful clinical tools through exploration and modern AI assistance? This project documents a complete learning journey from initial concept to working prototype, developing an adaptive emergency department surveillance system while respecting the distinction between clinical "vibe coding" and professional software engineering.

**Methods**
Starting from absolute beginner level (`print('Hello, World')`), I embarked on an intensive learning journey using open-source tools and de-identified MIMIC-IV-ED data. Over the course of one month, I developed a modular surveillance system combining gate-engine logic with machine learning. As a clinician applying systematic problem-solving skills to coding, I chose an adaptive architecture approach, leveraging extensive AI assistance for technical implementation while maintaining clinical oversight. The complete learning pathway—from first Python script to working prototype—is documented to show other clinicians what's possible with focused effort and modern learning tools.

**Results**
Starting from zero programming experience, I successfully developed an adaptive surveillance system generating real-time syndromic alerts while preserving privacy and workflow integration requirements. This journey began with a fun 2-day T5 fine-tuning experiment that sparked my interest in the possibilities of clinical AI development. More importantly, this demonstrates that clinical systematic thinking—particularly differential diagnosis approaches—translates powerfully to technical debugging and problem-solving. The complete learning pathway proves that intensive, focused learning with modern AI assistance can rapidly bridge the gap between clinical insight and technical implementation.

**Conclusions**
This work shows that individual clinicians can create sophisticated, adaptive AI systems without large teams or institutional infrastructure. The methodology provides a pathway for other healthcare professionals—particularly women in medicine—to explore AI development at their own pace and commitment level.

**Join the Journey**
Seeking other women in healthcare interested in collaborative AI development. No specific time commitments required—contribute as your schedule allows.

---

# Revised Paper

# From Curiosity to Code: A Clinician's Learning Journey in Healthcare AI Development

**Author:** Dr. med. Katharina Jacoby  
**Date:** 2025-08-29  
**Purpose:** Demonstrating accessible pathways to clinical AI development

---

## 1. Introduction: Clinical AI Development by Healthcare Professionals

The development of healthcare AI systems typically requires extensive technical teams and institutional resources. However, modern tools and AI assistance may enable individual healthcare professionals to create meaningful clinical applications. This paper documents the complete development process of an emergency department surveillance system, built by a single clinician with no prior programming experience.

The work began with a brief T5 fine-tuning experiment that demonstrated the feasibility of clinician-led AI development. This initial success sparked interest in developing a more comprehensive surveillance system addressing real emergency department coordination challenges. The project emphasizes transparent methodology, open-source development, and the application of clinical systematic thinking to technical problem-solving.

Rather than competing with professional engineering teams, this work explores how clinical domain expertise combined with modern development tools can contribute to healthcare AI innovation. The complete learning pathway and technical methodology are documented to enable replication and collaborative improvement by other healthcare professionals.

---

## 2. Why Adaptive Systems Matter

### Beyond Rigid Rules

Many clinical decision support systems follow fixed algorithms: if this, then that. But healthcare is inherently adaptive—experienced clinicians modify their approach based on patterns, context, and evolving understanding. Why shouldn't our AI tools do the same?

I chose a gate-engine architecture combined with machine learning specifically to create an adaptive system that could evolve with changing clinical patterns. While approaches like CatBoost regression models offer excellent performance for logistical optimization, I wanted something more flexible—a system that could learn from new patterns rather than being locked into predetermined pathways.

### The Solo Developer Advantage

Working alone actually offered some unexpected benefits:
- **Rapid iteration:** No committee decisions or approval processes
- **Cohesive vision:** Clinical insight directly translated to technical implementation
- **Authentic documentation:** Real-time capture of the actual development process
- **Transparent AI collaboration:** Clear documentation of how AI assistance enhanced rather than replaced clinical thinking

---

## 3. My Month-Long Learning Sprint: From Zero to Working Prototype

### The Complete Learning Timeline

**Week 1: Python Fundamentals + Data Access**
- Day 1: Literally `print('Hello, World')` - my first Python script
- Days 2-3: Pandas, data manipulation, basic programming concepts  
- Days 4-7: MIMIC-IV-ED access, understanding medical data structures
- **Key insight:** Clinical experience helped me understand what the data *meant*, even when I didn't yet understand the *code*

**Week 2: Feature Engineering Meets Clinical Logic**
- Days 8-10: Translating clinical intuition into computable features (this was surprisingly intuitive!)
- Days 11-14: Learning scikit-learn, machine learning basics
- **Key insight:** Differential diagnosis thinking transfers beautifully to feature selection

**Week 3: Building the Adaptive System**
- Days 15-18: Gate-engine + ML architecture (lots of AI assistance here!)
- Days 19-21: Debugging, testing, learning from failures
- **Key insight:** Clinical systematic problem-solving works for debugging code too

**Week 4: Integration and Polish** 
- Days 22-25: Real-time scoring, workflow integration
- Days 26-30: Documentation, code cleanup, preparing to share
- **Parallel project:** Also fine-tuned a T5 medical diagnosis model (complete debugging journey documented separately)

### What This Learning Curve Actually Looked Like

**Total Time Investment:**
- **Learning fundamentals:** ~60 hours (Python, pandas, ML basics)  
- **Active development:** ~100 hours (building, testing, debugging)
- **Documentation:** ~30 hours (essential for sharing and reflection)
- **Timeline:** One intensive month of focused learning and development
- **AI assistance:** Extensive throughout - probably 50% of my coding time

**My "Vibe Coding" Reality:**
- Start with clinical logic: "What would an experienced ED nurse track?"
- Ask AI: "How do I code this idea?"
- Debug systematically when things break (clinical differential diagnosis approach)
- Document everything because I knew I'd forget how I solved problems
- Repeat until it works, then document some more

---

## 4. Technical Approach: Adaptive by Design

### 4.1 Why Gate-Engine + ML?

**Traditional Approach (Rigid):**
```
Clinical Rule → Fixed Decision → Static Outcome
```

**My Adaptive Approach:**
```
Clinical Gate → ML Evaluation → Adaptive Response → Learning Update
```

The gate-engine provides clinical logic and safety boundaries, while the ML component adapts to patterns and provides probabilistic insights. This hybrid approach offers both interpretability and flexibility.

### 4.2 Architecture Decisions

**Data Processing:**
- Hourly feature aggregation for real-time capabilities
- Robust handling of missing data (common in ED workflows)
- Clinical feature engineering guided by emergency medicine experience

**Anomaly Detection:**
The machine learning component aims to identify unusual patterns in emergency department flow and clinical presentations that might indicate emerging syndromes or system stress. However, defining appropriate labels for "normal" versus "anomalous" patterns remains challenging, as many variations in ED patterns may be clinically insignificant or represent normal operational fluctuations rather than meaningful alerts.

- Isolation Forest for unsupervised pattern recognition
- Adaptive thresholds based on historical patterns
- Integration with clinical gate logic for actionable alerts

**Workflow Integration:**
- Designed to enhance rather than replace clinical judgment
- Modular architecture allowing selective adoption
- Real-time scoring capabilities

### 4.3 AI Assistance Integration

Throughout development, I used AI assistance for:
- Code optimization and debugging
- Documentation generation and review
- Error handling and edge case identification
- Architecture design discussions

**Key principle:** AI assistance enhanced my clinical thinking rather than replacing it. Every technical decision was reviewed through a clinical lens.

---

## 5. Results and Insights

### 5.1 Technical Implementation
The surveillance system successfully processes MIMIC-IV-ED data to generate real-time syndromic alerts while preserving privacy and workflow integration requirements. The adaptive gate-engine approach demonstrated greater flexibility than traditional rule-based alternatives, though validation on diverse datasets remains necessary.

### 5.2 Development Process Insights
**AI Assistance Integration:**
AI assistance proved valuable for code generation and maintaining daily development summaries, enabling rapid iteration while maintaining clinical oversight. However, debugging consumed the majority of development time and required systematic clinical problem-solving approaches rather than automated solutions.

**Feature Engineering Success:**
Clinical domain knowledge proved essential for meaningful feature selection. Emergency medicine experience directly informed which patterns to monitor (patient flow, acuity distributions, temporal variations) and how to structure them for machine learning analysis.

**Workflow Design:**
The modular, non-intrusive architecture allows integration with existing clinical systems without disrupting established workflows, addressing a common barrier to clinical AI adoption.

### 5.3 Community Building Lessons

**Documentation matters as much as code:**
- Other clinicians need to understand the journey, not just the destination
- Transparent methodology builds trust and enables replication
- Sharing struggles as well as successes helps others learn

**The power of invitation:**
- Many healthcare professionals are curious about AI development
- Lower barriers to entry encourage exploration
- Flexible collaboration models accommodate busy clinical schedules

---

## 6. Resources and Replication Guide

### 6.1 What You Need to Start

**Essential Requirements:**
- Curiosity about healthcare AI
- Basic comfort with learning new technical skills
- Access to a computer and internet connection
- Willingness to document your journey for others

**Helpful Background:**
- Clinical experience in any healthcare domain
- Basic programming familiarity (any language)
- Understanding of your local clinical workflows

**Not Required:**
- Advanced computer science background
- Institutional IT support
- Large time commitments (progress at your own pace)

### 6.2 My Development Setup

**Hardware:** Standard laptop (nothing special required)
**Software:** All free and open-source
- Python via Anaconda distribution
- Kaggle notebooks for development and sharing
- GitHub for version control and collaboration
- Standard scientific libraries (pandas, scikit-learn, etc.)

**Data:** MIMIC-IV-ED (free with research training completion)
**AI Assistant:** Transparent use for coding support with clinical oversight

### 6.3 Timeline Expectations

**Realistic timeframes based on my experience:**
- **Weekend explorer:** Basic understanding and first experiments
- **Month-long project:** Working prototype with documentation
- **Ongoing development:** Continuous improvement and adaptation
- **Community building:** Connecting with others and collaborative projects

---

## 7. Invitation to Join

### 7.1 Seeking Women in Healthcare

As a woman in medicine who successfully navigated this AI development journey, I'm particularly interested in connecting with other women in healthcare who are curious about building clinical AI tools. 

**Why focus on women?**
- Representation matters in healthcare AI development
- Diverse perspectives improve clinical relevance and safety
- Creating supportive spaces for learning and collaboration
- Demonstrating that AI development is accessible to all healthcare professionals

**No pressure, all welcome:**
- Contribute at whatever pace works for your life
- Share ideas, ask questions, or just observe
- Bring your clinical expertise—technical skills can be learned
- Help shape the future of healthcare AI from a clinical perspective

### 7.2 Flexible Collaboration Model

**Ways to Engage (choose what fits your schedule):**

**Curious Observer:**
- Follow the project and learn from shared resources
- Ask questions and share clinical insights
- No coding required—clinical perspective is valuable

**Occasional Contributor:**
- Try tutorials when you have time
- Share feedback on clinical relevance
- Suggest improvements based on your domain expertise

**Active Collaborator:**
- Adapt methodology to your clinical area
- Contribute code improvements or new features
- Help with validation studies or documentation

**Project Leader:**
- Lead development of specialty-specific adaptations
- Organize multi-site collaboration efforts
- Mentor newcomers to healthcare AI development

### 7.3 Connect With Me

**GitHub:** https://github.com/KatharinaJacoby  
**Kaggle:** https://www.kaggle.com/kjacoby  
**Hugging Face:** https://discuss.huggingface.co/u/katharina112/  
**Discord:** katharina_98697

---

## 8. Current Status and Next Steps

### 8.1 What's Working

**Technical achievements:**
- Complete surveillance system with real-time capabilities
- Adaptive architecture that learns from patterns
- Privacy-preserving design suitable for clinical environments
- Documented methodology for replication and adaptation

**Personal achievements:**
- Proof that solo clinical AI development is feasible
- Demonstration of effective AI-assisted development workflow
- Creation of accessible pathway for other healthcare professionals
- Open-source contribution to clinical AI community

### 8.2 Areas for Growth

**Technical improvements:**
- Multi-site validation beyond MIMIC-IV-ED
- Enhanced syndrome detection with clinical NLP
- Integration testing with live clinical workflows
- Performance optimization for larger-scale deployment

**Community building:**
- Connections with other women in healthcare AI
- Collaborative projects with diverse clinical perspectives
- Educational resources for healthcare professionals
- Advocacy for accessible clinical AI development

### 8.3 Long-term Vision

I hope this work contributes to a future where:
- Healthcare professionals feel empowered to build their own AI tools
- Clinical insight drives AI development rather than being an afterthought
- Women in medicine have strong representation in healthcare AI
- Adaptive, learning systems become the norm rather than rigid rule-based approaches
- Collaboration happens naturally across clinical and technical boundaries

Not through massive institutional programs, but through individual healthcare professionals taking the initiative to learn, build, and share—one clinician at a time, one project at a time, one collaboration at a time.

---

## 9. Conclusion: The Journey Continues

One month ago, I was a clinician curious about AI development. Today, I have a working surveillance system and a methodology that others can follow. Tomorrow, I hope to connect with other healthcare professionals who want to explore what's possible when we combine clinical insight with adaptive AI tools.

This isn't the end of a project—it's the beginning of a journey. A journey that I hope other women in healthcare will join, not because they need to commit to specific timelines or outcomes, but because they're curious about what we might build together.

The tools are accessible. The methodology is proven. The invitation is open.

**What will you build?**

---

## Appendix A: Complete Development Timeline

### Week-by-Week Breakdown
**Week 1: Foundation**
- Day 1-2: MIMIC-IV access setup, initial data exploration
- Day 3-4: Understanding ED workflow and surveillance requirements  
- Day 5-7: Feature engineering design with clinical logic

**Week 2: Implementation** 
- Day 8-10: Core feature pipeline development
- Day 11-12: Gate-engine architecture design
- Day 13-14: ML integration and anomaly detection

**Week 3: Integration**
- Day 15-17: Real-time scoring pipeline
- Day 18-19: Alert system and clinical workflow integration
- Day 20-21: Testing and validation with synthetic scenarios

**Week 4: Documentation and Sharing**
- Day 22-24: Code documentation and cleanup
- Day 25-27: Methodology documentation for replication
- Day 28-30: Open-source preparation and community outreach

### Time Investment Details
- **Average daily effort:** 2-3 hours
- **Peak development days:** 4-5 hours on weekends
- **AI assistance:** ~30% of coding time, 100% clinically supervised
- **Documentation:** 25% of total effort (essential for sharing)

---

## Appendix B: Resources and Next Steps

**Complete Code and Documentation:** https://github.com/KatharinaJacoby
- Full implementation with detailed comments
- Step-by-step tutorials for adaptation to other domains
- Privacy and ethics guidelines for clinical AI development
- Templates for collaborative development

**Community Connections:**
- **GitHub:** https://github.com/KatharinaJacoby
- **Kaggle:** https://www.kaggle.com/kjacoby  
- **Hugging Face:** https://discuss.huggingface.co/u/katharina112/
- **Discord:** katharina_98697

**Getting Started Guide:**
1. Review the GitHub repository and documentation
2. Complete MIMIC-IV data access (free research training required)
3. Try the introductory tutorial (estimated 10 hours over 1-2 weekends)
4. Connect with the growing community of healthcare AI developers
5. Share your clinical perspective and start building

---

*"Every expert was once a beginner. Every journey starts with a single step. Every community begins with one person willing to share what they've learned."*