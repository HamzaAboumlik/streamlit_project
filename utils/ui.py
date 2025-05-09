import streamlit as st
import base64
import os



def apply_global_css():
    st.markdown("""
        <style>
            :root {
                --fedex-purple: #4D148C;
                --fedex-orange: #FF6600;
            }

            html, body, .stApp {
                margin: 0;
                padding: 0;
            }

            .navbar {
                background-color: white;
                padding: 8px 20px;
                border-bottom: 2px solid var(--fedex-purple);
                position: sticky;
                top: 0;
                width: 100%;
                z-index: 999;
                box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
            }

         
            .nav-buttons {
                display: flex;
                justify-content: center;
                align-items: center;
                gap: 15px;
                margin-top: 0;
            }

            .stButton>button {
                background: none;
                border: none;
                color: var(--fedex-purple);
                font-weight: bold;
                font-size: 16px;
                padding: 6px 16px;
                cursor: pointer;
                border-radius: 5px;
                transition: all 0.3s;
            }

            .stButton>button:hover {
                background-color: #f0e6ff;
            }

            .active-btn {
                background-color: var(--fedex-orange) !important;
                color: white !important;
            }

            .content {
                padding-top: 70px;  /* add space to avoid content under navbar */
            }
            
        </style>
    """, unsafe_allow_html=True)



def render_navbar():
    pages = {
        "Dashboard": "../app.py",
        "Utilisateurs": "1_Utilisateurs.py",
        "Matériel": "2_Materiel.py",
        "Affectation": "3_Affectation.py",
        "Profile": "4_Profile.py"
    }

    if "current_page" not in st.session_state:
        st.session_state.current_page = "Dashboard"



    st.markdown('<div class="navbar">', unsafe_allow_html=True)
    col1, col2 = st.columns([1, 5])

    with col2:
        st.markdown('<div class="nav-buttons">', unsafe_allow_html=True)
        nav_cols = st.columns(len(pages))
        for i, (label, page_file) in enumerate(pages.items()):
            is_active = st.session_state.current_page == label
            with nav_cols[i]:
                if st.button(label, key=f"nav_{label}"):
                    st.session_state.current_page = label
                    st.switch_page(f"pages/{page_file}")

            if is_active:
                st.markdown(f"""
                    <style>
                        [data-testid="stButton"][key="nav_{label}"] > button {{
                            background-color: var(--fedex-orange);
                            color: white;
                        }}
                    </style>
                """, unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
