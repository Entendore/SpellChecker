import streamlit as st
import spacy
from io import StringIO
from core import AdvancedTextCorrector, apply_corrections

# --- Session State Initialization ---
# This ensures the model is loaded only once
if 'corrector' not in st.session_state:
    with st.spinner("Loading NLP models... This may take a moment."):
        try:
            nlp_model = spacy.load("en_core_web_sm")
            st.session_state.corrector = AdvancedTextCorrector(nlp_model=nlp_model)
        except Exception as e:
            st.error(f"Failed to load models: {e}")
            st.stop()

st.set_page_config(layout="wide")
st.title("✍️ Advanced NLP Corrector")

# --- Sidebar for Navigation ---
page = st.sidebar.selectbox("Choose a mode", ["Interactive Mode", "File Mode", "Add Word"])

corrector = st.session_state.corrector

# --- Page 1: Interactive Mode ---
if page == "Interactive Mode":
    st.header("Interactive Text Correction")
    user_input = st.text_area("Enter text to check:", height=200)
    
    if st.button("Check Text"):
        if user_input:
            errors = corrector.correct_text(user_input)
            if not errors:
                st.success("No errors found!")
            else:
                st.warning(f"Found {len(errors)} potential error(s).")
                user_decisions = {}
                for i, error in enumerate(errors):
                    with st.expander(f"Error {i+1}: '{error['original']}' ({error['type']})"):
                        st.write(f"**Suggestion:** {error['suggestion']}")
                        if error['type'] == 'grammar':
                            st.info(error['message'])
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            if st.button(f"Accept", key=f"accept_{i}"):
                                user_decisions[error['index']] = error['suggestion']
                        with col2:
                            if st.button(f"Ignore", key=f"ignore_{i}"):
                                user_decisions[error['index']] = 'ignore'
                        with col3:
                            own_correction = st.text_input("Your correction:", key=f"own_{i}")
                            if own_correction:
                                user_decisions[error['index']] = own_correction

                if st.button("Apply All Corrections"):
                    final_text = apply_corrections(user_input, errors, user_decisions)
                    st.subheader("Final Corrected Text")
                    st.info(final_text)

# --- Page 2: File Mode ---
elif page == "File Mode":
    st.header("File Correction")
    uploaded_file = st.file_uploader("Upload a .txt file", type="txt")
    
    if uploaded_file is not None:
        stringio = StringIO(uploaded_file.getvalue().decode("utf-8"))
        original_text = stringio.read()
        st.text_area("Original Text", original_text, height=200, disabled=True)

        if st.button("Process File"):
            with st.spinner("Correcting file..."):
                errors = corrector.correct_text(original_text)
                corrected_text = original_text
                # Apply all suggestions automatically
                for error in sorted(errors, key=lambda x: x['index'], reverse=True):
                    corrected_text = corrected_text[:error['index']] + error['suggestion'] + corrected_text[error['index'] + len(error['original']):]
                
                st.success(f"Corrected {len(errors)} errors.")
                st.subheader("Corrected Text")
                st.text_area("Corrected Text", corrected_text, height=200)
                
                st.download_button(
                    label="Download Corrected File",
                    data=corrected_text,
                    file_name=f"corrected_{uploaded_file.name}",
                    mime="text/plain"
                )

# --- Page 3: Add Word ---
elif page == "Add Word":
    st.header("Add a Word to Your Dictionary")
    new_word = st.text_input("Enter a word to add:")
    
    if st.button("Add Word"):
        if new_word:
            result = corrector.add_word(new_word)
            if "Success" in result:
                st.success(result)
            else:
                st.info(result)
        else:
            st.warning("Please enter a word.")