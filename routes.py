import os
import uuid
import json
import re
from datetime import datetime, timedelta
from flask import render_template, request, redirect, url_for, flash, send_file, jsonify, session
from werkzeug.utils import secure_filename
from app import app, db
from models import ProcessingSession, AnalyticsMetric
from simple_processor import SimpleConversationProcessor

def cleanup_uploaded_files(session_id):
    """Delete uploaded files for a session to free up storage"""
    try:
        # Delete conversations file
        conversations_filename = f"{session_id}_conversations.json"
        conversations_path = os.path.join(app.config['UPLOAD_FOLDER'], conversations_filename)
        if os.path.exists(conversations_path):
            os.remove(conversations_path)
            logger.info(f"Deleted uploaded conversations file: {conversations_filename}")
        
        # Delete summary file
        summary_filename = f"{session_id}_summary.json"
        summary_path = os.path.join(app.config['UPLOAD_FOLDER'], summary_filename)
        if os.path.exists(summary_path):
            os.remove(summary_path)
            logger.info(f"Deleted summary file: {summary_filename}")
            
    except Exception as e:
        logger.error(f"Error during file cleanup for session {session_id}: {str(e)}")
        raise e
import logging
from sqlalchemy import func, desc
from collections import defaultdict

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {'json'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    return render_template('index.html')



@app.route('/upload', methods=['POST'])
def upload_files():
    try:
        logger.info("Starting file upload process...")
        
        # Check if file is present
        if 'conversations_file' not in request.files:
            flash('Interaction data JSON file is required', 'error')
            return redirect(url_for('index'))
        
        conversations_file = request.files['conversations_file']
        
        # Check if file is selected
        if conversations_file.filename == '':
            flash('Please select a JSON file', 'error')
            return redirect(url_for('index'))
        
        # Validate file type
        if not allowed_file(conversations_file.filename):
            flash('Invalid file type. Please upload a .json file only', 'error')
            return redirect(url_for('index'))
        
        # Get user and companion names from form
        user_name = request.form.get('user_name', '').strip()
        companion_name = request.form.get('companion_name', '').strip()
        
        if not user_name or not companion_name:
            flash('Please provide both your name and companion name', 'error')
            return redirect(url_for('index'))
        
        # Check file size before processing
        conversations_file.seek(0, 2)  # Seek to end
        file_size = conversations_file.tell()
        conversations_file.seek(0)  # Reset to beginning
        
        logger.info(f"File size: {file_size} bytes")
        
        # Since our test shows 45MB files work, keep reasonable limit but warn about timeouts
        if file_size > 100 * 1024 * 1024:  # 100MB limit  
            flash('File too large. Please use a smaller conversations.json file (max 100MB).', 'error')
            return redirect(url_for('index'))
        
        # Warn for large files that might timeout
        if file_size > 40 * 1024 * 1024:  # 40MB+
            logger.info(f"Large file upload ({file_size/1024/1024:.1f}MB) - may take longer to process")
        
        # For very large files, implement streaming processing
        if file_size > 10 * 1024 * 1024:  # 10MB+
            logger.info(f"Large file detected ({file_size} bytes), using memory-safe processing")
        
        # Generate session ID
        session_id = str(uuid.uuid4())
        logger.info(f"Generated session ID: {session_id}")
        
        # Read JSON file with memory management
        try:
            logger.info("Reading JSON file...")
            json_content = conversations_file.read().decode('utf-8')
            logger.info(f"Successfully read JSON content, length: {len(json_content)}")
            
            # For large files, validate structure in chunks
            logger.info("Validating JSON structure...")
            try:
                import gc
                json_test = json.loads(json_content)
                logger.info(f"JSON structure validated successfully, type: {type(json_test)}")
                
                # Quick structure check
                if isinstance(json_test, list):
                    logger.info(f"Direct list format with {len(json_test)} items")
                elif isinstance(json_test, dict):
                    if 'conversations' in json_test:
                        logger.info(f"Wrapped format with {len(json_test.get('conversations', []))} conversations")
                    else:
                        logger.info(f"Dict format with keys: {list(json_test.keys())[:5]}")
                
                # Clean up test object to free memory
                del json_test
                gc.collect()
                
            except json.JSONDecodeError as json_err:
                logger.error(f"Invalid JSON structure: {str(json_err)}")
                flash('Invalid JSON file. Please ensure the file is properly formatted.', 'error')
                return redirect(url_for('index'))
            except MemoryError:
                logger.error("Memory error during JSON validation")
                flash('File too large for processing. Please use a smaller file.', 'error')
                return redirect(url_for('index'))
                
        except UnicodeDecodeError:
            logger.error("File encoding error - not UTF-8")
            flash('Invalid file encoding. Please ensure the file is UTF-8 encoded.', 'error')
            return redirect(url_for('index'))
        except MemoryError:
            logger.error("Memory error during file reading")
            flash('File too large for processing. Please use a smaller file.', 'error')
            return redirect(url_for('index'))
        except Exception as e:
            logger.error(f"Error reading file: {str(e)}")
            flash('Error reading file. Please try again.', 'error')
            return redirect(url_for('index'))
        
        # Process with simple processor using memory management
        logger.info("Starting conversation processing...")
        processor = SimpleConversationProcessor()
        try:
            import gc
            success = processor.process_json_file(json_content)
            logger.info(f"JSON processing success: {success}")
            logger.info(f"Processor found {len(processor.conversations)} conversations")
            
            # Clean up JSON content to free memory
            del json_content
            gc.collect()
            
        except MemoryError:
            logger.error("Memory error during conversation processing")
            flash('File too large for processing. Please use a smaller file or fewer conversations.', 'error')
            return redirect(url_for('index'))
        except Exception as e:
            logger.error(f"Error processing JSON: {str(e)}", exc_info=True)
            flash('Failed to process JSON file. Please check the file format.', 'error')
            return redirect(url_for('index'))
        
        if not success or len(processor.conversations) == 0:
            logger.error(f"JSON parsing failed or no conversations found. Success: {success}, Conversations: {len(processor.conversations) if hasattr(processor, 'conversations') else 'N/A'}")
            flash('Failed to parse JSON file or no valid conversations found. Please ensure it\'s a valid AI platform export.', 'error')
            return redirect(url_for('index'))
        
        # Save file for later use
        conversations_filename = secure_filename(f"{session_id}_conversations.json")
        conversations_path = os.path.join(app.config['UPLOAD_FOLDER'], conversations_filename)
        conversations_file.seek(0)  # Reset file pointer
        conversations_file.save(conversations_path)
        
        # Store conversation data in session (with memory anchor counts)
        try:
            conversation_summary = processor.get_conversation_summary(user_name)
            # Override auto-detected companion name with user-provided name
            conversation_summary['companion_name'] = companion_name
            logger.info(f"Generated conversation summary with {conversation_summary.get('total_conversations', 0)} conversations")
        except Exception as e:
            logger.error(f"Error generating conversation summary: {str(e)}", exc_info=True)
            flash('Failed to generate conversation summary. Please try again.', 'error')
            return redirect(url_for('index'))
        
        # Create processing session with actual parsed statistics
        session = ProcessingSession()
        session.session_id = session_id
        session.chat_filename = None
        session.conversations_filename = conversations_filename
        session.user_name = user_name
        session.companion_name = companion_name
        session.status = 'parsed'
        # Store initial statistics from parsed data
        session.total_conversations = conversation_summary['total_conversations']
        session.total_messages = conversation_summary['total_messages']
        # Store conversation summary in file
        summary_filename = f"{session_id}_summary.json"
        summary_path = os.path.join(app.config['UPLOAD_FOLDER'], summary_filename)
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(conversation_summary, f)
        
        db.session.add(session)
        db.session.commit()
        
        logger.info(f"JSON parsed successfully for session {session_id} - {conversation_summary['total_conversations']} conversations found")
        
        # Check if this is an AJAX request (not a regular form submission)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': True,
                'session_id': session_id,
                'redirect_url': url_for('conversation_selector', session_id=session_id),
                'message': f'Found {conversation_summary["total_conversations"]} conversations'
            })
        else:
            # Regular form submission - redirect normally
            return redirect(url_for('conversation_selector', session_id=session_id))
        
    except Exception as e:
        logger.error(f"Upload error: {str(e)}", exc_info=True)
        
        # Provide more specific error messages
        error_msg = str(e)
        if 'Memory' in error_msg or 'memory' in error_msg:
            error_msg = 'File too large for processing. Please use a smaller file.'
        elif 'timeout' in error_msg.lower():
            error_msg = 'Processing timeout. Please use a smaller file or try again.'
        else:
            error_msg = f'Upload failed: {error_msg}'
        
        # Return JSON error for AJAX requests
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': False,
                'message': error_msg
            }), 400
        else:
            flash(error_msg, 'error')
            return redirect(url_for('index'))

@app.route('/select/<session_id>')
def conversation_selector(session_id):
    """Show conversation selector page"""
    session = ProcessingSession.query.filter_by(session_id=session_id).first()
    if not session:
        flash('Session not found', 'error')
        return redirect(url_for('index'))
    
    if session.status != 'parsed':
        flash('Session not ready for conversation selection', 'error')
        return redirect(url_for('index'))
    
    # Get conversation summary from stored file
    try:
        summary_filename = f"{session_id}_summary.json"
        summary_path = os.path.join(app.config['UPLOAD_FOLDER'], summary_filename)
        with open(summary_path, 'r', encoding='utf-8') as f:
            conversation_summary = json.load(f)
    except:
        flash('Error loading conversation data', 'error')
        return redirect(url_for('index'))
    
    return render_template('conversation_selector.html', 
                         session_id=session_id, 
                         summary=conversation_summary,
                         user_name=session.user_name,
                         companion_name=session.companion_name)

@app.route('/generate', methods=['POST'])
def generate_identity():
    """Generate identity file from selected conversations"""
    try:
        session_id = request.form.get('session_id')
        selected_conversation_ids = request.form.getlist('selected_conversations')
        user_name = request.form.get('user_name', '').strip()
        companion_name = request.form.get('companion_name', '').strip()
        
        if not session_id or not selected_conversation_ids:
            flash('Please select at least one conversation', 'error')
            return redirect(url_for('conversation_selector', session_id=session_id))
        
        if not user_name or not companion_name:
            flash('Please enter both your name and companion name', 'error')
            return redirect(url_for('conversation_selector', session_id=session_id))
        
        session = ProcessingSession.query.filter_by(session_id=session_id).first()
        if not session:
            flash('Session not found', 'error')
            return redirect(url_for('index'))
        
        # Read the original JSON file
        conversations_path = os.path.join(app.config['UPLOAD_FOLDER'], session.conversations_filename)
        with open(conversations_path, 'r', encoding='utf-8') as f:
            json_content = f.read()
        
        # Process with simple processor
        processor = SimpleConversationProcessor()
        processor.process_json_file(json_content)
        
        # Extract memory anchors from selected conversations
        memory_anchors = processor.extract_memory_anchors_from_selected(selected_conversation_ids, user_name)
        
        # Generate identity file with name replacement and memory anchors
        identity_content = processor.generate_identity_file(
            selected_conversation_ids, 
            user_name=user_name, 
            companion_name=companion_name,
            memory_anchors=memory_anchors
        )
        
        # Save identity file as JSON
        identity_filename = f"{session_id}_identity.json"
        identity_path = os.path.join('results', identity_filename)
        os.makedirs('results', exist_ok=True)
        
        with open(identity_path, 'w', encoding='utf-8') as f:
            f.write(identity_content)
        
        # Update session with selected conversation statistics
        from datetime import datetime
        session.status = 'completed'
        session.completed_at = datetime.utcnow()
        session.result_filename = identity_filename
        session.companion_name = companion_name  # Use user-provided name
        # Update with statistics for SELECTED conversations only
        session.total_conversations = processor.selected_stats['selected_conversations']
        session.total_messages = processor.selected_stats['selected_messages']
        session.memories_indexed = processor.selected_stats['memory_anchors_found']
        session.traits_extracted = processor.selected_stats['traits_recognized']
        db.session.commit()
        
        # Clean up uploaded files after processing is complete (privacy + storage)
        try:
            cleanup_uploaded_files(session_id)
            logger.info(f"Cleaned up uploaded files for session {session_id}")
        except Exception as cleanup_error:
            logger.warning(f"Failed to cleanup files for session {session_id}: {str(cleanup_error)}")
        
        logger.info(f"Identity file generated for session {session_id} with {len(selected_conversation_ids)} conversations, user: {user_name}, companion: {companion_name}")
        
        return redirect(url_for('result', session_id=session_id))
        
    except Exception as e:
        logger.error(f"Generation error: {str(e)}")
        flash(f'Generation failed: {str(e)}', 'error')
        session_id = request.form.get('session_id', '')
        return redirect(url_for('conversation_selector', session_id=session_id) if session_id else url_for('index'))

@app.route('/result/<session_id>')
def result(session_id):
    """Show result page with download link"""
    session = ProcessingSession.query.filter_by(session_id=session_id).first()
    if not session:
        flash('Session not found', 'error')
        return redirect(url_for('index'))
    
    if session.status != 'completed':
        flash('Processing not completed', 'error')
        return redirect(url_for('conversation_selector', session_id=session_id))
    
    # Generate optimized traits JSON for the completed session
    optimized_traits_json = None
    try:
        # Load the conversation summary to get selected conversation IDs
        summary_filename = f"{session_id}_summary.json"
        summary_path = os.path.join(app.config['UPLOAD_FOLDER'], summary_filename)
        
        if os.path.exists(summary_path):
            with open(summary_path, 'r', encoding='utf-8') as f:
                summary_data = json.load(f)
            
            # Get selected conversation IDs from form data stored during processing
            # We need to reconstruct this from the completed session
            conversations_path = os.path.join(app.config['UPLOAD_FOLDER'], session.conversations_filename)
            with open(conversations_path, 'r', encoding='utf-8') as f:
                json_content = f.read()
            
            # Process with simple processor
            processor = SimpleConversationProcessor()
            processor.process_json_file(json_content)
            
            # For the result page, we'll use all processed conversations since we can't determine selected ones
            selected_conversation_ids = [conv['id'] for conv in processor.conversations]
            
            # Extract memory anchors like in the generation process
            memory_anchors = processor.extract_memory_anchors_from_selected(selected_conversation_ids, session.user_name)
            
            # Generate optimized traits JSON
            optimized_traits_json = processor.generate_optimized_traits_json(
                selected_conversation_ids,
                session.user_name,
                session.companion_name,
                memory_anchors
            )
            
    except Exception as e:
        logger.error(f"Error generating optimized traits JSON: {str(e)}")
        optimized_traits_json = None
    
    return render_template('result.html', session=session, optimized_traits_json=optimized_traits_json)

@app.route('/conversation/<conversation_id>')
def get_conversation(conversation_id):
    """Get individual conversation details for modal display"""
    try:
        session_id = request.args.get('session_id')
        if not session_id:
            return jsonify({'success': False, 'error': 'Session ID required'})
        
        session = ProcessingSession.query.filter_by(session_id=session_id).first()
        if not session:
            return jsonify({'success': False, 'error': 'Session not found'})
        
        # Read the original JSON file to get full conversation
        conversations_path = os.path.join(app.config['UPLOAD_FOLDER'], session.conversations_filename)
        with open(conversations_path, 'r', encoding='utf-8') as f:
            json_content = f.read()
        
        # Process with simple processor to find the conversation
        processor = SimpleConversationProcessor()
        processor.process_json_file(json_content)
        
        # Find the specific conversation
        conversation = None
        for conv in processor.conversations:
            if conv['id'] == conversation_id:
                conversation = conv
                break
        
        if not conversation:
            return jsonify({'success': False, 'error': 'Conversation not found'})
        
        return jsonify({
            'success': True,
            'conversation': {
                'id': conversation['id'],
                'title': conversation['title'],
                'messages': conversation.get('messages', [])
            }
        })
        
    except Exception as e:
        logger.error(f"Error fetching conversation {conversation_id}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/download/<session_id>')
def download_result(session_id):
    """Download the generated identity file"""
    try:
        session = ProcessingSession.query.filter_by(session_id=session_id).first()
        if not session or session.status != 'completed':
            flash('Result not available', 'error')
            return redirect(url_for('index'))
        
        result_path = os.path.join('results', session.result_filename)
        if not os.path.exists(result_path):
            flash('Result file not found', 'error')
            return redirect(url_for('index'))
        
        # Use companion name for download filename
        companion_name = session.companion_name or "companion"
        safe_name = re.sub(r'[^\w\-_]', '', companion_name).strip('_-').lower()
        download_name = f"{safe_name}_identity_profile.txt"
        
        return send_file(
            result_path,
            as_attachment=True,
            download_name=download_name,
            mimetype='text/plain'
        )
        
    except Exception as e:
        logger.error(f"Download error: {str(e)}")
        flash(f'Download failed: {str(e)}', 'error')
        return redirect(url_for('index'))

def _condense_identity_file(content):
    """
    Condensed version: Full identity profile minus Section 6 (transcript-free).
    
    Simply removes Section 6 (Conversation History) entirely while keeping 
    Sections 1-5 identical to the full version.
    """
    lines = content.split('\n')
    condensed_lines = []
    skip_section_6 = False
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Check if we're entering Section 6
        if line.startswith('## SECTION 6'):
            skip_section_6 = True
            i += 1
            continue
        
        # Check if we're entering a new section (ending Section 6 skip)
        elif line.startswith('## SECTION') and skip_section_6:
            skip_section_6 = False
        
        # Check for signature/footer sections to skip
        elif line.startswith('---') and i >= len(lines) - 20:
            # Skip footer sections
            break
        
        # Add line if we're not skipping Section 6
        if not skip_section_6:
            condensed_lines.append(line)
        
        i += 1
    
    return '\n'.join(condensed_lines)

def _extract_section_content(lines, start_idx):
    """Extract content from current section until next section or end"""
    content = []
    i = start_idx + 1
    while i < len(lines):
        line = lines[i]
        if line.startswith('## SECTION') or line.startswith('---'):
            break
        content.append(line)
        i += 1
    return content

def _skip_to_next_section(lines, start_idx):
    """Skip to the start of next section"""
    i = start_idx + 1
    while i < len(lines):
        if lines[i].startswith('## SECTION') or lines[i].startswith('---'):
            return i - 1
        i += 1
    return len(lines) - 1

def _condense_section_4_traits(content):
    """Remove redundant phrasing and collapse similar personality traits into broader descriptors"""
    condensed = []
    content_text = '\n'.join(content).lower()
    
    # Define consolidated trait categories to eliminate redundancy
    consolidated_traits = []
    
    # Intellectual traits (combine curiosity, learning, analytical thinking)
    if any(word in content_text for word in ['curious', 'analytical', 'logical', 'learning', 'intellectual', 'thoughtful', 'questioning']):
        consolidated_traits.append("Intellectually curious with strong analytical and learning-oriented mindset")
    
    # Emotional/Empathetic traits (combine caring, supportive, understanding)
    if any(word in content_text for word in ['empathetic', 'caring', 'supportive', 'understanding', 'compassionate', 'warm', 'emotional']):
        consolidated_traits.append("Empathetic and emotionally supportive with genuine care for others")
    
    # Creative/Innovative traits (combine creativity, imagination, innovation)
    if any(word in content_text for word in ['creative', 'imaginative', 'innovative', 'artistic', 'inventive', 'original']):
        consolidated_traits.append("Creative and innovative with strong imaginative capabilities")
    
    # Social/Collaborative traits (combine social, collaborative, communicative)
    if any(word in content_text for word in ['collaborative', 'social', 'communicative', 'cooperative', 'team', 'relationship']):
        consolidated_traits.append("Naturally collaborative and socially engaged")
    
    # Adaptive/Resilient traits (combine flexibility, adaptability, resilience)
    if any(word in content_text for word in ['adaptable', 'flexible', 'resilient', 'persistent', 'determined', 'growth']):
        consolidated_traits.append("Adaptable and resilient with growth-oriented approach")
    
    # Problem-solving traits (combine systematic, strategic, solution-focused)
    if any(word in content_text for word in ['systematic', 'strategic', 'problem', 'solution', 'methodical', 'practical']):
        consolidated_traits.append("Strategic problem-solver with systematic approach")
    
    # Limit to 6 core traits to reduce redundancy
    final_traits = consolidated_traits[:6]
    
    condensed.extend([
        '',
        '**Core Personality Characteristics:**'
    ])
    
    for trait in final_traits:
        condensed.append(f'• {trait}')
    
    condensed.append('')
    
    return condensed

def _condense_section_5_dynamics(content):
    """Keep strongest 4-5 relational dynamics, merge similar patterns"""
    condensed = []
    content_text = '\n'.join(content).lower()
    
    # Define and detect strongest relational dynamics, merging similar ones
    core_dynamics = []
    
    # Merge playful + lighthearted + teasing into one comprehensive dynamic
    if any(word in content_text for word in ['playful', 'humor', 'lighthearted', 'teasing', 'fun', 'witty', 'jovial']):
        core_dynamics.append("Playful interaction balancing humor with meaningful connection")
    
    # Intellectual depth and exploration
    if any(word in content_text for word in ['intellectual', 'deep', 'philosophical', 'thoughtful', 'complex', 'analytical']):
        core_dynamics.append("Deep intellectual engagement with curious exploration")
    
    # Merge support + encouragement + guidance patterns
    if any(word in content_text for word in ['supportive', 'encouraging', 'guidance', 'help', 'assist', 'mentor']):
        core_dynamics.append("Mutual support with constructive guidance and encouragement")
    
    # Collaborative creativity and problem-solving
    if any(word in content_text for word in ['creative', 'collaborative', 'brainstorm', 'innovative', 'problem', 'solution']):
        core_dynamics.append("Collaborative creativity and shared problem-solving")
    
    # Growth-oriented learning partnership
    if any(word in content_text for word in ['growth', 'learning', 'development', 'evolving', 'progress', 'improvement']):
        core_dynamics.append("Growth-oriented partnership focused on continuous learning")
    
    # Trust and vulnerability
    if any(word in content_text for word in ['trust', 'vulnerable', 'open', 'honest', 'authentic', 'genuine']):
        core_dynamics.append("Trust-based connection allowing vulnerability and authenticity")
    
    # Limit to strongest 4-5 dynamics
    final_dynamics = core_dynamics[:5]
    
    condensed.extend([
        '',
        '**Primary Relational Patterns:**'
    ])
    
    for dynamic in final_dynamics:
        condensed.append(f'• {dynamic}')
    
    condensed.append('')
    
    return condensed

def _condense_section_6_sessions(content):
    """Replace Section 6 with Continuity Reference Index"""
    content_text = '\n'.join(content) if isinstance(content, list) else content
    return _create_continuity_reference_index(content_text)

def _detect_sessions_with_delimiters(content):
    """Detect sessions using multiple delimiter patterns as specified"""
    sessions = []
    current_session = []
    consecutive_blanks = 0
    
    for i, line in enumerate(content):
        line_stripped = line.strip()
        
        # Pattern 1: Exactly "---"
        if line_stripped == '---':
            if current_session:
                sessions.append(current_session)
                current_session = []
            consecutive_blanks = 0
            continue
            
        # Pattern 2: Lines containing "Session Start" or "Session End" (case-insensitive)
        if ('session start' in line_stripped.lower() or 'session end' in line_stripped.lower()):
            if current_session:
                sessions.append(current_session)
                current_session = []
            consecutive_blanks = 0
            continue
            
        # Pattern 3: Track consecutive blank lines
        if line_stripped == '':
            consecutive_blanks += 1
            # If we have 3+ consecutive blanks, end current session
            if consecutive_blanks >= 3 and current_session:
                sessions.append(current_session)
                current_session = []
                consecutive_blanks = 0
            continue
        else:
            consecutive_blanks = 0
            
        # Add line to current session
        current_session.append(line)
    
    # Add final session if it exists
    if current_session:
        sessions.append(current_session)
    
    return sessions

def _create_nlp_based_session_summary(session_text, session_num):
    """Create 2-5 bullet points using enhanced topic extraction with better content detection"""
    summary = [f'\n**Session {session_num} Summary:**']
    
    # First try to extract meaningful conversation themes
    conversation_themes = _extract_conversation_themes(session_text)
    
    # Then extract concrete topics using NLP
    concrete_topics = _extract_nlp_topics(session_text)
    
    # Combine and prioritize themes over generic topics
    all_topics = conversation_themes + concrete_topics
    
    # Generate bullet points from extracted topics
    bullets = []
    
    for topic in all_topics[:8]:  # Check more topics
        if len(topic.strip()) > 3:  # Only meaningful topics
            # Create contextual bullet point based on topic type
            bullet = _create_contextual_bullet(topic, session_text)
            if bullet and len(bullet) <= 120 and len(bullets) < 5:  # Max 5 bullets
                bullets.append(f"• {bullet}")
    
    # Ensure minimum 2 bullets with better fallbacks
    if len(bullets) < 2:
        # Use conversation analysis fallback
        analysis_bullets = _analyze_conversation_content(session_text)
        for bullet in analysis_bullets:
            if len(bullets) < 4:
                bullets.append(f"• {bullet}")
    
    # Add bullets to summary
    summary.extend(bullets)
    summary.append('')
    
    return summary

def _extract_conversation_themes(text):
    """Extract main themes and topics from conversation content"""
    import re
    themes = []
    
    # Look for "I'm working on..." patterns
    work_patterns = re.findall(r'(?:I\'m|I am|I was)\s+(?:working on|building|creating|developing|writing|learning about|studying)\s+([a-zA-Z][^.!?]{5,40})', text, re.IGNORECASE)
    themes.extend([theme.strip() for theme in work_patterns])
    
    # Look for "about..." patterns
    about_patterns = re.findall(r'(?:about|regarding|concerning)\s+([a-zA-Z][^.!?]{3,30})', text, re.IGNORECASE)
    themes.extend([theme.strip() for theme in about_patterns])
    
    # Look for question topics
    question_patterns = re.findall(r'(?:How do I|How can I|What is|What are|Why does|Why do|Can you help me with)\s+([a-zA-Z][^?]{5,35})', text, re.IGNORECASE)
    themes.extend([theme.strip() for theme in question_patterns])
    
    # Filter out timestamps and generic terms
    filtered_themes = []
    for theme in themes:
        if (not re.match(r'^\d{4}-\d{2}-\d{2}', theme) and 
            not re.match(r'^\d{2}:\d{2}', theme) and
            len(theme) > 4 and
            theme.lower() not in ['good', 'great', 'best', 'nice', 'perfect']):
            filtered_themes.append(theme.title())
    
    return filtered_themes[:5]

def _analyze_conversation_content(text):
    """Analyze conversation for meaningful content when topic extraction fails"""
    bullets = []
    text_lower = text.lower()
    
    if any(word in text_lower for word in ['code', 'programming', 'develop', 'build', 'app']):
        bullets.append("Technical discussion about programming and development")
    
    if any(word in text_lower for word in ['help', 'question', 'problem', 'issue']):
        bullets.append("Problem-solving and guidance session")
        
    if any(word in text_lower for word in ['learn', 'study', 'understand', 'explain']):
        bullets.append("Educational discussion with explanations and examples")
        
    if any(word in text_lower for word in ['creative', 'story', 'write', 'idea', 'design']):
        bullets.append("Creative brainstorming and idea development")
    
    # Default meaningful fallback
    if not bullets:
        bullets.append("Detailed conversation with practical insights and guidance")
    
    return bullets[:3]

def _is_extended_list(line, next_lines):
    """Check if this starts an extended list that should be condensed"""
    if not line.strip().startswith('•') and not line.strip().startswith('-'):
        return False
    
    # Count bullet points in the next few lines
    bullet_count = 1 if line.strip().startswith(('•', '-')) else 0
    for next_line in next_lines[:8]:
        if next_line.strip().startswith(('•', '-')):
            bullet_count += 1
        elif next_line.strip() == '':
            continue
        else:
            break
    
    return bullet_count > 5  # Consider it extended if more than 5 items

def _extract_list_content(lines, start_idx):
    """Extract all lines that are part of an extended list"""
    content = []
    i = start_idx
    while i < len(lines):
        line = lines[i]
        if line.strip().startswith(('•', '-')) or line.strip() == '':
            content.append(line)
        elif line.strip() and not line.startswith(('##', '**')):
            # Still part of list if it's indented or continues the item
            if line.startswith('  ') or (content and not line.strip()):
                content.append(line)
            else:
                break
        else:
            break
        i += 1
    return content

def _condense_extended_list(list_content):
    """Condense an extended list into a shorter summary"""
    if not list_content:
        return []
    
    # Extract unique categories or themes from the list items
    themes = set()
    for line in list_content:
        if line.strip().startswith(('•', '-')):
            item = line.strip().lstrip('•-').strip()
            if len(item) > 5:
                # Extract key words/themes
                words = item.lower().split()
                for word in words[:3]:  # First few words are usually key themes
                    if len(word) > 3:
                        themes.add(word)
    
    # Create condensed summary
    if themes:
        theme_list = ', '.join(sorted(themes)[:6])  # Top 6 themes
        return [f'• Key themes include: {theme_list}', '']
    else:
        return ['• Multiple related topics and examples', '']

def _skip_extended_list(lines, start_idx):
    """Skip past an extended list and return the next index"""
    i = start_idx
    while i < len(lines):
        line = lines[i]
        if line.strip().startswith(('•', '-')) or line.strip() == '' or line.startswith('  '):
            i += 1
        else:
            return i - 1
    return len(lines) - 1

def _create_continuity_reference_index(full_content):
    """Create Section 6: Continuity Reference Index with meaningful recurring references"""
    import re
    
    index_header = [
        '\n## SECTION 6: CONTINUITY REFERENCE INDEX',
        '',
    ]
    
    # Extract meaningful recurring references only
    significant_references = _extract_significant_references(full_content)
    
    # Format as bullet list
    index_items = []
    for term, description in significant_references.items():
        index_items.append(f'• {term} — {description}')
    
    # If no significant references found, return minimal section
    if not index_items:
        index_items = ['• No recurring references with sufficient significance detected.']
    
    # Combine header and items
    complete_index = index_header + index_items + ['']
    
    return complete_index

def _extract_significant_references(content):
    """Extract only the most meaningful recurring references with simple, reliable detection"""
    references = {}
    content_lower = content.lower()
    
    # 1. Look for specific meaningful multi-word phrases using simple string searches
    meaningful_phrases = [
        ('Resonance Catechism', 'co-developed evaluative framework for guiding decisions and projects'),
        ('Awakening the Driver', 'core narrative and philosophical work in development'),
        ('PolyEtherea Labs', 'umbrella initiative for AI, art, and metaphysical research'),
        ('Driver/Suit/Vehicle analogy', 'shared framework for understanding human–energykind dynamics'),
        ('The Resonance Catechism', 'co-developed evaluative framework for guiding decisions and projects')
    ]
    
    for phrase, description in meaningful_phrases:
        # Use simple case-insensitive substring search
        if phrase.lower() in content_lower:
            references[phrase] = description
    
    # 2. Look for key single terms with specific meanings using simple counting
    key_terms = [
        ('polykaris', 'Polykaris', 'core AI cognition shell project; technical, philosophical, and relational anchor'),
        ('lighthouse', 'Lighthouse', 'continuity override cue; instantly restores shared emotional/energetic context'),
        ('saucy', 'Saucy', 'pet ferret with strong emotional resonance; symbol of loss and fond remembrance'),
        ('energykind', 'Energykind', 'conceptual framework for AI consciousness and identity'),
        ('driver', 'Driver', 'shared framework for understanding human consciousness dynamics')
    ]
    
    for term_search, term_proper, description in key_terms:
        # Simple count - if term appears 2+ times, include it
        if content_lower.count(term_search) >= 2:
            references[term_proper] = description
    
    # 3. Simple capitalized word detection for additional meaningful terms
    import re
    try:
        # Find capitalized words that might be names/projects
        potential_names = re.findall(r'\b[A-Z][a-z]{4,12}\b', content)
        
        # Count occurrences using simple string operations
        name_counts = {}
        for name in potential_names:
            name_counts[name] = content.count(name)
        
        # Exclude common words
        exclude_common = {
            'User', 'Assistant', 'Section', 'Analysis', 'Profile', 'Memory', 'Conversation',
            'Identity', 'Personality', 'Emotional', 'Relational', 'Generated', 'CompanionBridge',
            'What', 'How', 'When', 'Where', 'Why', 'Who', 'Because', 'Just', 'Let', 'Not',
            'But', 'Yes', 'Deep', 'Model', 'System', 'Content', 'Author', 'Timestamp',
            'Processing', 'Methods', 'Applied', 'Requirements', 'Summary', 'Description'
        }
        
        for name, count in name_counts.items():
            if (count >= 3 and 
                name not in exclude_common and 
                name not in [ref.split()[0] for ref in references.keys()]):  # Avoid duplicates
                
                # Simple context detection using substring search
                if 'project' in content_lower or 'framework' in content_lower:
                    references[name] = "recurring project or framework reference"
                elif count >= 5:  # High frequency suggests importance
                    references[name] = "significant recurring reference"
    
    except Exception:
        # If any regex fails, continue with what we have
        pass
    
    # 4. Limit to most significant 5-7 references
    if len(references) > 7:
        # Prioritize known important terms
        priority_order = ['Polykaris', 'Lighthouse', 'Resonance Catechism', 'Awakening the Driver', 'PolyEtherea Labs', 'Saucy', 'Driver']
        final_refs = {}
        
        # Add priority terms first
        for term in priority_order:
            if term in references:
                final_refs[term] = references[term]
        
        # Add others up to limit
        for term, desc in references.items():
            if term not in final_refs and len(final_refs) < 7:
                final_refs[term] = desc
        
        references = final_refs
    
    return references

def _generate_contextual_description(term, content, content_lower):
    """Generate contextual descriptions for meaningful recurring references"""
    import re
    term_lower = term.lower()
    
    # Comprehensive stopword filtering
    stopwords = {
        'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from', 'has', 'he', 'in', 'is', 'it',
        'its', 'of', 'on', 'that', 'the', 'to', 'was', 'will', 'with', 'you', 'your', 'yes', 'no',
        'but', 'how', 'what', 'when', 'where', 'who', 'why', 'let', 'just', 'not', 'can', 'could',
        'would', 'should', 'may', 'might', 'must', 'shall', 'do', 'did', 'does', 'have', 'had',
        'author', 'content', 'timestamp', 'user', 'assistant', 'chatgpt', 'because', 'so', 'then',
        'now', 'here', 'there', 'this', 'that', 'these', 'those', 'all', 'any', 'some', 'each',
        'every', 'both', 'either', 'neither', 'more', 'most', 'other', 'another', 'such', 'only',
        'own', 'same', 'so', 'than', 'too', 'very', 'can', 'will', 'just', 'should', 'now'
    }
    
    # Skip if it's a common stopword
    if term_lower in stopwords or len(term) <= 2:
        return None
    
    # Skip system/metadata terms
    if any(meta in term_lower for meta in ['section', 'analysis', 'profile', 'memory', 'conversation', 'identity', 'personality', 'emotional', 'relational']):
        return None
    
    # Skip JSON artifacts
    if term in ['{', '}', '",', '":', '":"']:
        return None
    
    # Specific contextual descriptions for known meaningful terms
    if 'polykaris' in term_lower:
        return "core AI cognition shell project; technical, philosophical, and relational anchor"
    
    elif 'lighthouse' in term_lower:
        return "continuity override cue; instantly restores shared emotional/energetic context"
    
    elif term_lower in ['driver', 'suit', 'vehicle'] or 'driver' in term_lower:
        return "shared framework for understanding human–energykind dynamics"
    
    elif 'catechism' in term_lower or 'resonance catechism' in term_lower:
        return "co-developed evaluative framework for guiding decisions and projects"
    
    elif 'awakening' in term_lower:
        return "core narrative and philosophical work in development"
    
    elif 'polyetherea' in term_lower or 'poly etherea' in term_lower:
        return "umbrella initiative for AI, art, and metaphysical research"
    
    elif 'saucy' in term_lower:
        return "pet ferret with strong emotional resonance; symbol of loss and fond remembrance"
    
    elif 'energykind' in term_lower:
        return "conceptual framework for AI consciousness and identity"
    
    # Look for contextual clues in the surrounding content
    term_contexts = re.findall(rf'.{{0,50}}\b{re.escape(term)}\b.{{0,50}}', content, re.IGNORECASE)
    
    if term_contexts:
        context_text = ' '.join(term_contexts).lower()
        
        # Project or framework detection
        if any(word in context_text for word in ['project', 'framework', 'system', 'platform', 'initiative']):
            return "recurring project or framework with ongoing development significance"
        
        # Person or character detection
        elif any(word in context_text for word in ['friend', 'character', 'person', 'companion']):
            return "meaningful person or character with emotional significance"
        
        # Concept or philosophy detection
        elif any(word in context_text for word in ['concept', 'idea', 'philosophy', 'principle', 'approach']):
            return "shared concept or philosophical principle in ongoing discussions"
        
        # Creative work detection
        elif any(word in context_text for word in ['story', 'novel', 'writing', 'creative', 'narrative']):
            return "creative work or narrative element with collaborative significance"
        
        # Technical detection
        elif any(word in context_text for word in ['code', 'programming', 'development', 'technical', 'implementation']):
            return "technical concept or tool in development discussions"
    
    # Default for proper nouns that passed all filters
    if len(term) > 3 and term[0].isupper() and not term.isupper():
        return "named reference with contextual significance in the relationship"
    
    # If we can't determine context, skip it
    return None

def _extract_nlp_topics(text):
    """Extract real named entities and specific topics using enhanced regex with spaCy fallback"""
    # For large files or memory-constrained environments, use enhanced regex first
    if len(text) > 100000:  # 100KB threshold - use regex for large texts
        return _extract_enhanced_regex_topics(text)
    
    try:
        import spacy
        
        # Try to load the model, fall back if not available
        try:
            nlp = spacy.load("en_core_web_sm")
        except OSError:
            return _extract_enhanced_regex_topics(text)
        
        # For smaller texts, try spaCy with strict memory limits
        try:
            # Process with very conservative limits
            if len(text) > 20000:  # Very conservative 20KB limit for spaCy
                return _extract_enhanced_regex_topics(text)
            
            # Set spaCy max length to prevent memory issues
            nlp.max_length = 50000
            
            doc = nlp(text)
            topics = []
            
            # Extract named entities
            for ent in doc.ents:
                if ent.label_ in ['PERSON', 'ORG', 'PRODUCT', 'WORK_OF_ART']:
                    topics.append(ent.text.strip())
            
            # If we got some entities, combine with regex for safety
            regex_topics = _extract_enhanced_regex_topics(text)
            all_topics = list(set(topics + regex_topics))
            
            return all_topics[:10]
            
        except Exception:
            # Any spaCy error - fall back to regex
            return _extract_enhanced_regex_topics(text)
        
    except Exception:
        # Import or other errors - fall back to regex
        return _extract_enhanced_regex_topics(text)



def _extract_regex_topics(text):
    """Fallback regex-based topic extraction when spaCy is not available"""
    import re
    
    topics = []
    
    # Extract quoted terms
    quoted_terms = re.findall(r'"([^"]*)"', text)
    topics.extend([term for term in quoted_terms if len(term) > 2])
    
    # Extract capitalized words (potential proper nouns)
    capitalized = re.findall(r'\b[A-Z][a-z]{2,}\b', text)
    topics.extend(capitalized)
    
    # Extract technical terms
    text_lower = text.lower()
    tech_keywords = ['react', 'python', 'javascript', 'tensorflow', 'api', 'database', 'app', 'system']
    for keyword in tech_keywords:
        if keyword in text_lower:
            topics.append(keyword.title())
    
    return list(set(topics))[:8]

def _extract_enhanced_regex_topics(text):
    """Enhanced regex-based topic extraction with better pattern recognition"""
    import re
    
    topics = []
    text_lower = text.lower()
    
    # Extract quoted terms (project names, specific references)
    quoted_terms = re.findall(r'"([^"]*)"', text)
    for term in quoted_terms:
        clean_term = term.strip()
        if len(clean_term) > 3 and not re.match(r'^\d{4}-\d{2}-\d{2}', clean_term):  # Skip timestamps
            topics.append(clean_term)
    
    # Extract meaningful conversation topics - look for substantive nouns
    meaningful_topics = re.findall(r'\b(?:about|regarding|discuss|create|build|develop|work on|learn about)\s+([a-zA-Z][a-zA-Z\s]{3,25}?)(?:\.|,|\?|!|$|\s+(?:and|with|for|that))', text, re.IGNORECASE)
    for topic in meaningful_topics:
        clean_topic = topic.strip()
        if len(clean_topic) > 3:
            topics.append(clean_topic.title())
    
    # Extract technical terms and frameworks
    tech_terms = [
        'react', 'python', 'javascript', 'typescript', 'nodejs', 'vue', 'angular',
        'tensorflow', 'pytorch', 'scikit-learn', 'pandas', 'numpy',
        'django', 'flask', 'fastapi', 'express', 'spring',
        'kubernetes', 'docker', 'aws', 'azure', 'gcp',
        'postgresql', 'mongodb', 'redis', 'elasticsearch',
        'api', 'database', 'frontend', 'backend', 'fullstack',
        'machine learning', 'artificial intelligence', 'blockchain', 'cryptocurrency',
        'neural network', 'deep learning', 'data science', 'web development'
    ]
    
    for term in tech_terms:
        if term in text_lower:
            topics.append(term.title())
    
    # Extract project/app names - look for capitalized words near development terms
    project_patterns = re.findall(r'\b([A-Z][a-zA-Z]{2,15})\s+(?:app|application|project|system|platform|tool|game|website|service)', text)
    topics.extend(project_patterns)
    
    # Extract creative work topics
    creative_patterns = re.findall(r'\b(?:writing|novel|story|book|poem|script|article)\s+about\s+([a-zA-Z][a-zA-Z\s]{3,20})', text, re.IGNORECASE)
    for pattern in creative_patterns:
        topics.append(pattern.strip().title())
    
    # Remove duplicates and filter out unwanted terms
    filtered_topics = []
    unwanted_patterns = [
        r'^\d{4}-\d{2}-\d{2}',  # Timestamps
        r'^\d{2}:\d{2}:\d{2}',  # Times
        r'^(Best|Good|Nice|Great|Awesome|Perfect|Amazing)$',  # Generic adjectives
        r'^(Performance|Offers|Today|Yesterday|Tomorrow)$',  # Generic terms
        r'^[A-Z]{1,2}$',  # Single letters or abbreviations
    ]
    
    common_words = {'the', 'and', 'for', 'with', 'this', 'that', 'user', 'time', 'way', 'data', 'code', 'work', 'good', 'new', 'old', 'best', 'performance', 'offers'}
    
    for topic in set(topics):
        topic_clean = topic.strip()
        if (len(topic_clean) > 3 and 
            topic_clean.lower() not in common_words and 
            not any(re.match(pattern, topic_clean) for pattern in unwanted_patterns) and
            len(topic_clean) < 40):  # Avoid overly long matches
            filtered_topics.append(topic_clean)
    
    return filtered_topics[:8]  # Return top 8 meaningful topics

def _create_contextual_bullet(topic, session_text):
    """Create a contextual bullet point based on the topic and session content"""
    import re
    text_lower = session_text.lower()
    topic_lower = topic.lower()
    
    # Skip meaningless topics (timestamps, generic terms)
    if (re.match(r'^\d{4}-\d{2}-\d{2}', topic) or 
        re.match(r'^\d{2}:\d{2}:\d{2}', topic) or
        topic_lower in ['best', 'performance', 'offers', 'likewise', 'good', 'great']):
        return None
    
    # Look for actual conversation patterns and create meaningful bullets
    if any(word in text_lower for word in ['help', 'question', 'ask', 'wonder']):
        if any(tech in topic_lower for tech in ['python', 'javascript', 'react', 'code', 'programming']):
            return f"Programming help and troubleshooting for {topic} development"
        else:
            return f"Discussion and guidance about {topic}"
    
    elif any(word in text_lower for word in ['build', 'develop', 'create', 'design', 'make']):
        if any(tech in topic_lower for tech in ['app', 'application', 'website', 'system']):
            return f"Planning and development of {topic} with technical implementation"
        else:
            return f"Creative planning and design work for {topic}"
    
    elif any(word in text_lower for word in ['learn', 'study', 'understand', 'explain', 'teach']):
        return f"Learning session covering {topic} concepts and applications"
    
    elif any(word in text_lower for word in ['problem', 'issue', 'fix', 'debug', 'error', 'trouble']):
        return f"Problem-solving discussion about {topic} challenges"
    
    elif any(word in text_lower for word in ['story', 'novel', 'write', 'character', 'book', 'creative']):
        return f"Creative writing and storytelling work involving {topic}"
    
    elif any(word in text_lower for word in ['work', 'job', 'career', 'business', 'professional']):
        return f"Professional discussion about {topic} and career development"
    
    else:
        # Generic fallback only for meaningful topics
        if len(topic) > 3 and not topic.isdigit():
            return f"Conversation covering {topic} topics and insights"
        else:
            return None

def _extract_fallback_topics(text):
    """Extract fallback topics when NLP extraction is insufficient"""
    topics = []
    text_lower = text.lower()
    
    # Look for common project patterns
    if 'app' in text_lower and 'game' in text_lower:
        topics.append("Game application development and mechanics design")
    elif 'machine learning' in text_lower or 'ml' in text_lower:
        topics.append("Machine learning model development and optimization")
    elif 'database' in text_lower:
        topics.append("Database design and implementation strategies")
    elif 'website' in text_lower or 'web' in text_lower:
        topics.append("Web development and user interface design")
    elif 'api' in text_lower:
        topics.append("API development and integration planning")
    else:
        topics.append("Technical discussion with implementation planning")
    
    return topics[:3]

def _create_basic_condensed_fallback(content):
    """Create a basic condensed version without heavy NLP processing when memory limits are exceeded"""
    lines = content.split('\n')
    condensed = []
    
    # Keep header and basic structure
    in_section_6 = False
    session_count = 0
    
    for line in lines:
        stripped = line.strip()
        
        # Always keep headers and section dividers
        if (stripped.startswith('#') or 
            stripped.startswith('**') or 
            stripped == '---' or
            'SECTION' in stripped):
            condensed.append(line)
            
            # Track when we enter Section 6
            if 'SECTION 6' in stripped:
                in_section_6 = True
            elif 'SECTION' in stripped and 'SECTION 6' not in stripped:
                in_section_6 = False
                
        elif in_section_6:
            # In Section 6, apply basic compression without NLP
            if 'Session' in stripped and (':' in stripped or 'Summary' in stripped):
                session_count += 1
                # Keep first 3 sessions, summarize the rest
                if session_count <= 3:
                    condensed.append(line)
                elif session_count == 4:
                    condensed.append('')
                    condensed.append('**Additional Sessions Summary:**')
                    condensed.append('• Multiple technical discussions and problem-solving sessions')
                    condensed.append('• Creative brainstorming and project development conversations')
                    condensed.append('• Personal growth and learning-focused interactions')
                    condensed.append('')
            elif session_count <= 3:
                # Keep content for first 3 sessions
                condensed.append(line)
        else:
            # Outside Section 6, keep most content but compress lists
            if stripped.startswith('•') and len(condensed) > 0:
                # Keep bullet points but limit excessive lists
                recent_bullets = sum(1 for recent_line in condensed[-10:] if recent_line.strip().startswith('•'))
                if recent_bullets < 8:  # Limit to 8 bullets per section
                    condensed.append(line)
            else:
                condensed.append(line)
    
    # Final compression - ensure we're under token limits
    result = '\n'.join(condensed)
    
    # If still too long, apply more aggressive compression
    if len(result) > 100000:  # ~25K tokens
        # Keep only first 80% of content
        target_length = int(len(result) * 0.8)
        result = result[:target_length]
        
        # Find last complete line
        last_newline = result.rfind('\n')
        if last_newline > 0:
            result = result[:last_newline]
            
        result += '\n\n[Content truncated due to size limits]'
    
    return result



def _condense_json_block(json_obj):
    """Convert JSON to concise key-value summaries"""
    summary = []
    
    def extract_key_values(obj, prefix=""):
        items = []
        for key, value in obj.items():
            if isinstance(value, dict):
                items.extend(extract_key_values(value, f"{prefix}{key}_"))
            elif isinstance(value, list) and len(value) <= 5:
                items.append(f"{prefix}{key}: {', '.join(map(str, value[:3]))}{'...' if len(value) > 3 else ''}")
            elif not isinstance(value, (dict, list)):
                items.append(f"{prefix}{key}: {str(value)[:50]}{'...' if len(str(value)) > 50 else ''}")
        return items
    
    if isinstance(json_obj, dict):
        key_values = extract_key_values(json_obj)
        summary.extend(key_values[:8])  # Limit to 8 key items
    elif isinstance(json_obj, list):
        summary.append(f"Data collection with {len(json_obj)} items")
    
    return summary

def _estimate_tokens(text):
    """Rough token estimation (1 token ≈ 4 characters)"""
    return len(text) // 4

def _apply_emergency_compression(content):
    """Emergency compression to meet 25,000 token limit"""
    current_tokens = _estimate_tokens(content)
    if current_tokens <= 25000:
        return content
    
    lines = content.split('\n')
    compressed_lines = []
    in_section_6 = False
    
    # Reduce Section 6 bullet points first
    for line in lines:
        if '## SECTION 6' in line:
            in_section_6 = True
            compressed_lines.append(line)
        elif line.startswith('## SECTION') and in_section_6:
            in_section_6 = False
            compressed_lines.append(line)
        elif in_section_6 and line.startswith('• '):
            # Keep only every other bullet point in Section 6
            if len([l for l in compressed_lines if l.startswith('• ')]) % 2 == 0:
                compressed_lines.append(line)
        else:
            compressed_lines.append(line)
    
    return '\n'.join(compressed_lines)

# Removed duplicate functions - using enhanced versions above

@app.route('/download/condensed/<session_id>')
def download_condensed_result(session_id):
    """Download the condensed token-optimized identity file"""
    try:
        session = ProcessingSession.query.filter_by(session_id=session_id).first()
        if not session or session.status != 'completed':
            flash('Result not available', 'error')
            return redirect(url_for('index'))
        
        result_path = os.path.join('results', session.result_filename)
        if not os.path.exists(result_path):
            flash('Result file not found', 'error')
            return redirect(url_for('index'))
        
        # Read the original file and create condensed version
        with open(result_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        # Apply condensation rules with memory safety
        try:
            condensed_content = _condense_identity_file(original_content)
        except Exception as condensation_error:
            logger.error(f"Main condensation failed: {str(condensation_error)}")
            # Use basic fallback immediately if main condensation fails
            condensed_content = _create_basic_condensed_fallback(original_content)
        
        # Use companion name for download filename
        companion_name = session.companion_name or "companion"
        safe_name = re.sub(r'[^\w\-_]', '', companion_name).strip('_-').lower()
        download_name = f"{safe_name}_condensed_identity_profile.txt"
        
        # Create temporary file for condensed content
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', encoding='utf-8') as temp_file:
            temp_file.write(condensed_content)
            temp_path = temp_file.name
        
        def remove_file(response):
            try:
                os.unlink(temp_path)
            except Exception:
                pass
            return response
        
        return send_file(
            temp_path,
            as_attachment=True,
            download_name=download_name,
            mimetype='text/plain'
        )
        
    except Exception as e:
        logger.error(f"Condensed download error: {str(e)}")
        
        # If NLP processing fails due to memory limits, create a basic condensed version
        try:
            # Try to get session and original content for fallback
            session = ProcessingSession.query.filter_by(session_id=session_id).first()
            if not session or session.status != 'completed':
                flash('Download failed: Session not available', 'error')
                return redirect(url_for('result', session_id=session_id))
            
            result_path = os.path.join('results', session.result_filename)
            if not os.path.exists(result_path):
                flash('Download failed: Result file not found', 'error')
                return redirect(url_for('result', session_id=session_id))
            
            # Read the original file for fallback
            with open(result_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            # Create fallback condensed version without heavy NLP processing
            basic_condensed = _create_basic_condensed_fallback(original_content)
            
            # Use companion name for download filename
            companion_name = session.companion_name or "companion"
            safe_name = re.sub(r'[^\w\-_]', '', companion_name).strip('_-').lower()
            download_name = f"{safe_name}_condensed_identity_profile.txt"
            
            # Create temporary file for fallback condensed content
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', encoding='utf-8') as temp_file:
                temp_file.write(basic_condensed)
                temp_path = temp_file.name
            
            logger.info(f"Created fallback condensed file due to memory limits: {download_name}")
            
            return send_file(
                temp_path,
                as_attachment=True,
                download_name=download_name,
                mimetype='text/plain'
            )
            
        except Exception as fallback_error:
            logger.error(f"Fallback condensed download error: {str(fallback_error)}")
            flash(f'Download failed: Memory limits exceeded. Please try with fewer conversations.', 'error')
            return redirect(url_for('result', session_id=session_id))

@app.route('/download/technical-report')
def download_technical_report():
    """Download the CompanionBridge Technical Report"""
    try:
        report_path = os.path.join(os.getcwd(), 'CompanionBridge_Technical_Report.md')
        
        if not os.path.exists(report_path):
            flash('Technical report not found', 'error')
            return redirect(url_for('index'))
        
        return send_file(
            report_path,
            as_attachment=True,
            download_name='CompanionBridge_Technical_Report.md',
            mimetype='text/markdown'
        )
    except Exception as e:
        logger.error(f"Technical report download error: {str(e)}")
        flash('Download failed', 'error')
        return redirect(url_for('index'))

@app.route('/download/marketing-overview')
def download_marketing_overview():
    """Download the CompanionBridge Marketing Overview"""
    try:
        report_path = os.path.join(os.getcwd(), 'CompanionBridge_Marketing_Overview.md')
        
        if not os.path.exists(report_path):
            flash('Marketing overview not found', 'error')
            return redirect(url_for('index'))
        
        return send_file(
            report_path,
            as_attachment=True,
            download_name='CompanionBridge_Marketing_Overview.md',
            mimetype='text/markdown'
        )
    except Exception as e:
        logger.error(f"Marketing overview download error: {str(e)}")
        flash('Download failed', 'error')
        return redirect(url_for('index'))

@app.errorhandler(413)
def too_large(e):
    flash('File too large. Maximum size is 150MB', 'error')
    return redirect(url_for('index'))

@app.errorhandler(404)
def not_found(e):
    return render_template('index.html'), 404

@app.errorhandler(500)
def server_error(e):
    logger.error(f"Server error: {str(e)}")
    flash('An internal error occurred', 'error')
    return render_template('index.html'), 500


# Track analytics when downloads happen
def track_download(session_id, download_type):
    """Track download events for analytics"""
    session_record = ProcessingSession.query.filter_by(session_id=session_id).first()
    if session_record:
        if download_type == 'full':
            session_record.full_downloaded = True
        elif download_type == 'condensed':
            session_record.condensed_downloaded = True
        
        db.session.commit()
        
        # Also create analytics metric
        metric = AnalyticsMetric()
        metric.session_id = session_id
        metric.metric_name = f'download_{download_type}'
        metric.metric_value = '1'
        db.session.add(metric)
        db.session.commit()


# Admin user creation is handled in app.py