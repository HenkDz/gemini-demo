"""
Browser automation tools with Browser-Use and Gemini.

This script demonstrates:
- Complex form filling with multiple steps
- File upload (documents)
- Cross-origin iframe handling
- Structured output with detailed summary
- Using Google's Gemini model for complex multi-step tasks
- SaaS idea discovery using Gummy search

Example workflows:
1. Application submission workflow:
   - Navigate to application page
   - Fill out personal information fields
   - Upload document
   - Complete optional/demographic fields
   - Submit application and confirm success

2. SaaS idea discovery workflow:
   - Search for niche SaaS ideas
   - Analyze market trends
   - Generate unique business concepts
"""

import argparse
import asyncio
import json
import os
import random

from browser_use import Agent, Browser, ChatGoogle, Tools
from browser_use.tools.views import UploadFileAction
from dotenv import load_dotenv

load_dotenv()


async def inject_results_overlay(page, results: str, title: str = "Results"):
    """
    Inject a results overlay into the page that displays the automation results.
    The overlay stays visible and the browser remains open for the user to inspect.
    """
    # Escape the results for JavaScript
    escaped_results = (
        results.replace("\\", "\\\\")
        .replace("`", "\\`")
        .replace("$", "\\$")
        .replace("\n", "\\n")
    )

    await page.evaluate(f"""() => {{
        // Remove any existing overlay
        const existing = document.getElementById('results-overlay');
        if (existing) existing.remove();

        // Create overlay container
        const overlay = document.createElement('div');
        overlay.id = 'results-overlay';
        overlay.style.cssText = `
            position: fixed;
            top: 0;
            right: 0;
            width: 450px;
            height: 100vh;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #e0e0e0;
            font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif;
            z-index: 2147483647;
            box-shadow: -5px 0 30px rgba(0, 0, 0, 0.5);
            display: flex;
            flex-direction: column;
            overflow: hidden;
        `;

        // Header
        const header = document.createElement('div');
        header.style.cssText = `
            padding: 20px;
            background: linear-gradient(90deg, #fe750e 0%, #fd8a3d 100%);
            color: black;
            font-weight: 600;
            font-size: 18px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        `;
        header.innerHTML = `
            <span>🎯 ${{`{title}`}}</span>
            <button id="close-overlay" style="
                background: rgba(0,0,0,0.2);
                border: none;
                color: black;
                width: 30px;
                height: 30px;
                border-radius: 50%;
                cursor: pointer;
                font-size: 16px;
            ">✕</button>
        `;

        // Content area
        const content = document.createElement('div');
        content.style.cssText = `
            flex: 1;
            overflow-y: auto;
            padding: 20px;
            line-height: 1.6;
            font-size: 14px;
        `;

        // Format the results with some basic styling
        const formattedResults = `{escaped_results}`
            .replace(/##\\s*(.+)/g, '<h3 style="color: #fd8a3d; margin-top: 20px; margin-bottom: 10px;">$1</h3>')
            .replace(/\\*\\*(.+?)\\*\\*/g, '<strong style="color: #fff;">$1</strong>')
            .replace(/\\n/g, '<br>');

        content.innerHTML = formattedResults;

        // Footer with copy button
        const footer = document.createElement('div');
        footer.style.cssText = `
            padding: 15px 20px;
            background: rgba(0,0,0,0.3);
            display: flex;
            gap: 10px;
        `;

        const copyBtn = document.createElement('button');
        copyBtn.textContent = '📋 Copy Results';
        copyBtn.style.cssText = `
            flex: 1;
            padding: 12px;
            background: #fe750e;
            color: black;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-weight: 600;
            font-size: 14px;
        `;
        copyBtn.onclick = () => {{
            navigator.clipboard.writeText(`{escaped_results}`);
            copyBtn.textContent = '✅ Copied!';
            setTimeout(() => copyBtn.textContent = '📋 Copy Results', 2000);
        }};

        const minimizeBtn = document.createElement('button');
        minimizeBtn.textContent = '➖';
        minimizeBtn.style.cssText = `
            width: 45px;
            padding: 12px;
            background: rgba(255,255,255,0.1);
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
        `;

        let minimized = false;
        minimizeBtn.onclick = () => {{
            minimized = !minimized;
            if (minimized) {{
                content.style.display = 'none';
                overlay.style.width = '60px';
                overlay.style.height = 'auto';
                overlay.style.top = '20px';
                overlay.style.right = '20px';
                overlay.style.borderRadius = '10px';
                header.style.display = 'none';
                footer.style.flexDirection = 'column';
                copyBtn.style.display = 'none';
                minimizeBtn.textContent = '📊';
            }} else {{
                content.style.display = 'block';
                overlay.style.width = '450px';
                overlay.style.height = '100vh';
                overlay.style.top = '0';
                overlay.style.right = '0';
                overlay.style.borderRadius = '0';
                header.style.display = 'flex';
                footer.style.flexDirection = 'row';
                copyBtn.style.display = 'block';
                minimizeBtn.textContent = '➖';
            }}
        }};

        footer.appendChild(copyBtn);
        footer.appendChild(minimizeBtn);

        overlay.appendChild(header);
        overlay.appendChild(content);
        overlay.appendChild(footer);

        document.body.appendChild(overlay);

        // Close button handler
        document.getElementById('close-overlay').onclick = () => overlay.remove();
    }}""")

    print("\n✅ Results displayed in browser overlay. Browser will stay open.")
    print("   You can copy the results or close the overlay when done.\n")


async def inject_start_button_and_wait(page):
    """
    Inject a two-step UI:
    1. 'FILL OUT APPLICATION' button
    2. Model selection dropdown + 'SUBMIT' button

    Uses JavaScript Promises to wait for user interactions.
    Returns the selected model name.
    """
    print(
        "\n🌐 Browser opened. Waiting for you to click 'FILL OUT APPLICATION' button..."
    )

    result = await page.evaluate("""() => {
        return new Promise((resolve) => {
            // Add CSS animation for entrance effect
            const style = document.createElement('style');
            style.textContent = `
                @keyframes slideUpFadeIn {
                    from {
                        opacity: 0;
                        transform: translateY(20px);
                    }
                    to {
                        opacity: 1;
                        transform: translateY(0);
                    }
                }
            `;
            document.head.appendChild(style);

            // Step 1: Create initial "FILL OUT APPLICATION" button
            const initialButton = document.createElement('button');
            initialButton.id = 'start-application-btn';
            initialButton.innerHTML = 'FILL OUT APPLICATION';

            // Style the button (modern design with Inter font)
            initialButton.style.cssText = `
                position: fixed;
                top: 20px;
                left: 20px;
                display: inline-flex;
                align-items: center;
                justify-content: center;
                white-space: nowrap;
                height: 38px;
                padding: 0 32px;
                background: #fe750e;
                color: black;
                font-family: Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                font-size: 14px;
                font-weight: 500;
                text-transform: uppercase;
                letter-spacing: 0.05em;
                border: 1px solid #fd8a3d;
                border-radius: 0;
                cursor: pointer;
                z-index: 2147483647;
                min-width: 180px;
                transition: all 0.2s ease;
                user-select: none;
                box-shadow: none;
                animation: slideUpFadeIn 0.6s ease-out;
            `;

            // Add hover effect
            initialButton.addEventListener('mouseenter', () => {
                initialButton.style.background = '#e66a0d';
                initialButton.style.boxShadow = '0 0 20px rgba(254, 117, 14, 0.4)';
            });

            initialButton.addEventListener('mouseleave', () => {
                initialButton.style.background = '#fe750e';
                initialButton.style.boxShadow = 'none';
            });

            // Click handler for initial button
            initialButton.addEventListener('click', () => {
                // Remove initial button
                initialButton.remove();

                // Step 2: Create model selection UI
                const container = document.createElement('div');
                container.id = 'model-selection-container';
                container.style.cssText = `
                    position: fixed;
                    top: 20px;
                    left: 20px;
                    display: flex;
                    gap: 8px;
                    z-index: 2147483647;
                `;

                // Create dropdown
                const dropdown = document.createElement('select');
                dropdown.id = 'model-dropdown';
                dropdown.style.cssText = `
                    height: 38px;
                    padding: 0 12px;
                    background: white;
                    color: black;
                    font-family: Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                    font-size: 14px;
                    font-weight: 500;
                    border: 1px solid #fd8a3d;
                    border-radius: 0;
                    cursor: pointer;
                    outline: none;
                `;

                // Add options
                const options = [
                    { value: 'gemini-3-flash-preview', text: 'Google (gemini-3-flash-preview)' }
                ];

                options.forEach(opt => {
                    const option = document.createElement('option');
                    option.value = opt.value;
                    option.textContent = opt.text;
                    option.selected = true;  // Only one option, so it's always selected
                    dropdown.appendChild(option);
                });

                // Create submit button
                const submitButton = document.createElement('button');
                submitButton.id = 'submit-model-btn';
                submitButton.innerHTML = 'SUBMIT';
                submitButton.style.cssText = `
                    display: inline-flex;
                    align-items: center;
                    justify-content: center;
                    white-space: nowrap;
                    height: 38px;
                    padding: 0 32px;
                    background: #fe750e;
                    color: black;
                    font-family: Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                    font-size: 14px;
                    font-weight: 500;
                    text-transform: uppercase;
                    letter-spacing: 0.05em;
                    border: 1px solid #fd8a3d;
                    border-radius: 0;
                    cursor: pointer;
                    min-width: 120px;
                    transition: all 0.2s ease;
                    user-select: none;
                    box-shadow: none;
                `;

                // Submit button hover effects
                submitButton.addEventListener('mouseenter', () => {
                    submitButton.style.background = '#e66a0d';
                    submitButton.style.boxShadow = '0 0 20px rgba(254, 117, 14, 0.4)';
                });

                submitButton.addEventListener('mouseleave', () => {
                    submitButton.style.background = '#fe750e';
                    submitButton.style.boxShadow = 'none';
                });

                // Submit button click handler
                submitButton.addEventListener('click', () => {
                    const selectedModel = dropdown.value;

                    // Visual feedback
                    submitButton.style.background = '#d55f0c';
                    submitButton.style.opacity = '0.5';
                    submitButton.style.pointerEvents = 'none';
                    submitButton.innerHTML = 'STARTING...';
                    dropdown.disabled = true;
                    dropdown.style.opacity = '0.5';

                    // Remove UI after short delay
                    setTimeout(() => {
                        container.remove();
                    }, 500);

                    // Resolve with selected model
                    resolve(selectedModel);
                });

                // Append elements to container
                container.appendChild(dropdown);
                container.appendChild(submitButton);

                // Append container to body
                document.body.appendChild(container);
            });

            // Append initial button to body
            document.body.appendChild(initialButton);
        });
    }""")

    print(f"✓ User selected model: {result}. Starting automated form filling...\n")
    return result


async def apply_to_form(applicant_info: dict, document_path: str):
    """
    Submit application form with provided information.

    Expected JSON format in applicant_info:
    {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john.doe@example.com",
            "phone": "555-555-5555",
            "age": "21",
            "US_citizen": true,
            "sponsorship_needed": false,
            "postal_code": "12345",
            "country": "USA",
            "city": "Rochester",
            "address": "123 Main St",
            "gender": "Male",
            "race": "Asian",
            "Veteran_status": "Not a veteran",
            "disability_status": "No disability"
    }
    """

    # Use Gemini model for complex form filling tasks
    llm = ChatGoogle(model="gemini-3-flash-preview", thinking_budget=1)

    tools = Tools()

    # Flag to track if button has been clicked
    button_clicked = False

    @tools.action(description="Upload document file")
    async def upload_document(browser_session):
        params = UploadFileAction(path=document_path, index=0)
        return "Ready to upload document"

    @tools.action(description="Wait for user to click start button before proceeding")
    async def wait_for_start_button(browser_session):
        nonlocal button_clicked
        if not button_clicked:
            page = await browser_session.get_current_page()
            if page:
                await inject_start_button_and_wait(page)
                button_clicked = True
                return "User clicked start button - proceeding with form filling"
            else:
                return "Error: Could not get current page"
        return "Button already clicked, continuing"

    # Enable cross-origin iframe support for embedded application forms
    # Set headless=False so user can see the browser and click the button
    browser = Browser(cross_origin_iframes=True, headless=False)

    task = f"""
	- Your goal is to fill out and submit an application form with the provided information.
	- Navigate to https://apply.appcast.io/jobs/50590620606/applyboard/apply/
	- FIRST: Use the wait_for_start_button action immediately after navigation. This will show a button for the user to click.
	- WAIT for the user to click the button before continuing with any form filling.
	- Scroll through the entire application and use extract_structured_data action to extract all the relevant information needed to fill out the application form. use this information and return a structured output that can be used to fill out the entire form: {applicant_info}. Use the done action to finish the task. Fill out the application form with the following information.
		- Before completing every step, refer to this information for accuracy. It is structured in a way to help you fill out the form and is the source of truth.
	- Follow these instructions carefully:
		- if anything pops up that blocks the form, close it out and continue filling out the form.
		- Do not skip any fields, even if they are optional. If you do not have the information, make your best guess based on the information provided.
		Fill out the form from top to bottom, never skip a field to come back to it later. When filling out a field, only focus on one field per step. For each of these steps, scroll to the related text. These are the steps:
			1) use input_text action to fill out the following:
				- "First name"
				- "Last name"
				- "Email"
				- "Phone number"
			2) use the upload_file_to_element action to fill out the following:
				- Document upload field
			3) use input_text action to fill out the following:
				- "Postal code"
				- "Country"
				- "State"
				- "City"
				- "Address"
				- "Age"
			4) use click action to select the following options:
				- "Are you legally authorized to work in the country for which you are applying?"
				- "Will you now or in the future require sponsorship for employment visa status (e.g., H-1B visa status, etc.) to work legally for Rochester Regional Health?"
				- "Do you have, or are you in the process of obtaining, a professional license?"
					- SELECT NO FOR THIS FIELD
			5) use input_text action to fill out the following:
				- "What drew you to healthcare?"
			6) use click action to select the following options:
				- "How many years of experience do you have in a related role?"
				- "Gender"
				- "Race"
				- "Hispanic/Latino"
				- "Veteran status"
				- "Disability status"
			7) use input_text action to fill out the following:
				- "Today's date"
			8) CLICK THE SUBMIT BUTTON AND CHECK FOR A SUCCESS SCREEN. Once there is a success screen, complete your end task of writing final_result and outputting it.
	- Before you start, create a step-by-step plan to complete the entire task. make sure the delegate a step for each field to be filled out.
	*** IMPORTANT ***:
		- You are not done until you have filled out every field of the form.
		- When you have completed the entire form, press the submit button to submit the application and use the done action once you have confirmed that the application is submitted
		- PLACE AN EMPHASIS ON STEP 4, the click action. That section should be filled out.
		- At the end of the task, structure your final_result as 1) a human-readable summary of all detections and actions performed on the page with 2) a list with all questions encountered in the page. Do not say "see above." Include a fully written out, human-readable summary at the very end.
	"""

    # Make document file available for upload
    available_file_paths = [document_path]

    agent = Agent(
        task=task,
        llm=llm,
        demo_mode=True,
        browser=browser,
        tools=tools,
        available_file_paths=available_file_paths,
    )

    history = await agent.run()

    return history.final_result()


async def discover_saas_ideas(keep_browser_open: bool = True):
    """
    Search for niche SaaS ideas using Gummy search and market analysis.

    This function will:
    1. Search for current market trends and pain points
    2. Analyze existing solutions and gaps
    3. Generate unique SaaS concepts with business potential
    4. Present findings in a structured format

    Args:
        keep_browser_open: If True, displays results in browser overlay and keeps it open
    """

    # Use Gemini model for research and analysis
    llm = ChatGoogle(model="gemini-3-flash-preview", thinking_budget=1)

    browser = Browser(headless=False)
    tools = Tools()

    @tools.action(description="Search for niche markets and pain points")
    async def search_niche_markets(browser_session):
        page = await browser_session.get_current_page()

        # Navigate to Gummy search
        await page.goto("https://gummysearch.com/")
        await page.wait_for_timeout(2000)

        # Generate search terms for niche SaaS ideas
        search_terms = [
            "niche software as a service opportunities",
            "underserved business software markets",
            "b2b software pain points",
            "small business software gaps",
            "industry specific software needs",
        ]

        selected_term = random.choice(search_terms)

        # Enter search query
        await page.fill('input[placeholder*="Search" i]', selected_term)
        await page.keyboard.press("Enter")
        await page.wait_for_timeout(3000)

        return f"Searched for: {selected_term}"

    @tools.action(description="Extract relevant information from search results")
    async def extract_relevant_info(browser_session):
        page = await browser_session.get_current_page()

        # Extract content from the page
        content = await page.evaluate("""
        () => {
            // Get all text content from search results
            const elements = document.querySelectorAll('h1, h2, h3, p, li, span');
            const texts = Array.from(elements).map(el => el.textContent.trim());
            return texts.filter(text => text.length > 10).join('\n');
        }
        """)

        return f"Extracted content: {content[:5000]}"

    task = """
    Your goal is to discover interesting niche SaaS ideas using market research. Follow these steps:

    1. Use search_niche_markets to search for business pain points and underserved markets
    2. Use extract_relevant_info to gather information from the search results
    3. Analyze the information to identify:
       - Common pain points that aren't well addressed
       - Industry-specific needs that lack good solutions
       - Emerging trends that could create new opportunities
       - Gaps between existing solutions and market needs
    4. Generate 5-7 unique SaaS concepts based on your analysis. For each concept:
       - Name the product
       - Describe the problem it solves
       - Identify the target market
       - Outline key features
       - Explain why it's a good business opportunity

    5. Present your findings in a structured format with clear headings for each concept

    When complete, use the done action with a comprehensive summary of all the SaaS ideas you've discovered.
    """

    agent = Agent(
        task=task,
        llm=llm,
        demo_mode=True,
        browser=browser,
        tools=tools,
    )

    history = await agent.run()

    result = history.final_result()

    # Display results in browser overlay and keep browser open
    if keep_browser_open and result:
        try:
            # Get the current page from the browser context
            context = await browser.get_context()
            pages = context.pages
            if pages:
                page = pages[-1]  # Get the last active page
                await inject_results_overlay(page, result, "SaaS Ideas Discovery")

                # Keep the browser open by waiting for user input
                print("\n" + "=" * 60)
                print("📊 Results are displayed in the browser sidebar!")
                print("=" * 60)
                print("\nPress Enter to close the browser and exit...")

                # Use asyncio to wait for input without blocking
                await asyncio.get_event_loop().run_in_executor(None, input)
        except Exception as e:
            print(f"Note: Could not display overlay: {e}")
        finally:
            await browser.close()

    return result


async def main(
    applicant_data_path: str = None, document_path: str = None, mode: str = "apply"
):
    if mode == "apply":
        # Verify files exist before starting
        if not os.path.exists(applicant_data_path):
            raise FileNotFoundError(
                f"Applicant data file not found: {applicant_data_path}"
            )
        if not os.path.exists(document_path):
            raise FileNotFoundError(f"Document file not found: {document_path}")

        # Load applicant information from JSON
        with open(applicant_data_path) as f:  # noqa: ASYNC230
            applicant_info = json.load(f)

        print(f"\n{'=' * 60}")
        print("Starting Application Submission")
        print(f"{'=' * 60}")
        print(
            f"Applicant: {applicant_info.get('first_name')} {applicant_info.get('last_name')}"
        )
        print(f"Email: {applicant_info.get('email')}")
        print(f"Document: {document_path}")
        print(f"{'=' * 60}\n")

        # Submit the application
        result = await apply_to_form(applicant_info, document_path=document_path)

        # Display results
        print(f"\n{'=' * 60}")
        print("Application Result")
        print(f"{'=' * 60}")
        print(result)
        print(f"{'=' * 60}\n")

    elif mode == "saas":
        print(f"\n{'=' * 60}")
        print("Discovering Niche SaaS Ideas")
        print(f"{'=' * 60}\n")

        # Discover SaaS ideas
        result = await discover_saas_ideas()

        # Display results
        print(f"\n{'=' * 60}")
        print("SaaS Ideas Discovery Results")
        print(f"{'=' * 60}")
        print(result)
        print(f"{'=' * 60}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Browser automation tools with Browser-Use and Gemini",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Application submission mode (default)
  python main.py --document example_document.pdf

  # Use your own data for application
  python main.py --data my_info.json --document my_document.pdf

  # SaaS idea discovery mode
  python main.py --mode saas
		""",
    )
    parser.add_argument(
        "--mode",
        choices=["apply", "saas"],
        default="apply",
        help="Operation mode: 'apply' for form filling, 'saas' for idea discovery (default: apply)",
    )
    parser.add_argument(
        "--data",
        default="applicant_data.json",
        help="Path to applicant data JSON file (default: applicant_data.json)",
    )
    parser.add_argument(
        "--document",
        help="Path to document file (PDF format) - required for 'apply' mode",
    )

    args = parser.parse_args()

    # Validate arguments based on mode
    if args.mode == "apply" and not args.document:
        parser.error("--document is required for 'apply' mode")

    asyncio.run(main(args.data, args.document, args.mode))
