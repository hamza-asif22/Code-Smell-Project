from flask import Flask, render_template, request
import os
import ast
import zipfile
import tempfile
import shutil

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'py', 'zip'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def process_zip(file):
    """
    Extracts the uploaded zip file and detects code smells in all .py files inside.
    Returns a combined report.
    """
    temp_dir = tempfile.mkdtemp()
    try:
        with zipfile.ZipFile(file, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)

        python_files = [
            os.path.join(root, name)
            for root, _, files in os.walk(temp_dir)
            for name in files if name.endswith('.py')
        ]

        combined_report = "Combined Code Smells Report:\n"
        total_smells = 0

        for py_file in python_files:
            with open(py_file, 'r', encoding='utf-8') as f:
                code = f.read()
                report = detect_code_smells(code, max_function_length=100, max_long_param_list=5, max_class_size=200)
                combined_report += f"\n\n--- Analysis for File: {os.path.basename(py_file)} ---\n{report}"
                total_smells += report.count("\n- ") 

        combined_report += f"\n\nOverall Total Code Smells Detected: {total_smells}"
        return combined_report
    finally:
        shutil.rmtree(temp_dir)

def generate_report(smells_summary, max_limits):

    report = "Code Smells Detected:\n"

    # Unused Imports
    unused_imports = smells_summary.get('unused_imports', [])
    if unused_imports:
        report += f"\nUnused Imports:\n" + "\n".join(f"- {imp} (line {lineno})" for imp, lineno in unused_imports)
        report += "\n\nImpacts:\n Increase load times, more memory usage."
        report += "\n\nSolution:\nRemove the Un-used Import manually from the Code\n"
        report += f"\nTotal Unused Imports: {len(unused_imports)}"
    else:
        report += "\nNo unused imports detected."

    # Long Functions
    long_functions = smells_summary.get('long_functions', [])
    if long_functions:
        max_function_length = max_limits['function_length']
        report += f"\n\nLong Functions (>{max_function_length} lines):\n"
        report += "\n".join(f"- {name} (line {lineno}): {length} lines" for name, length, lineno in long_functions)
        report += "\n\nImpacts:\nIncrease Complexity, hard to test."
        report += "\n\nSolution:\nSplit the Function into smaller Functions\n"
        report += f"\nTotal Long Functions: {len(long_functions)}"
    else:
        report += f"\n\nNo functions longer than {max_limits['function_length']} lines detected."

    # Long Parameter Lists
    long_param_functions = smells_summary.get('long_param_functions', [])
    if long_param_functions:
        max_long_param_list = max_limits['param_list']
        report += f"\n\nLong Parameter Lists (>{max_long_param_list} parameters):\n"
        report += "\n".join(f"- {name} (line {lineno}): {num_params} parameters" for name, num_params, lineno in long_param_functions)
        report += "\n\nImpacts:\nDegrade runtime efficiency, reduce readability. "
        report += "\n\nSolution:\nSimplify and refactor the parameter list using strategies:\n"
        report += f"\nTotal Long Parameter Lists: {len(long_param_functions)}"
    else:
        report += f"\n\nNo functions with more than {max_limits['param_list']} parameters detected."

    # Large Classes
    large_classes = smells_summary.get('large_classes', [])
    if large_classes:
        max_class_size = max_limits['class_size']
        report += f"\n\nLarge Classes (>{max_class_size} lines):\n"
        report += "\n".join(f"- {name} (line {lineno}): {size} lines" for name, size, lineno in large_classes)
        report += "\n\nImpacts:\nReduces Maintainability, Hard to understand."
        report += "\n\nSolution:\n"
        report += "Split the Class into smaller Classes\n"
        report += f"\nTotal Large Classes: {len(large_classes)}"
    else:
        report += f"\n\nNo large classes detected."



    # Total Smells
    total_smells = sum(len(items) for items in smells_summary.values())
    report += f"\n\nTotal Code Smells Detected: {total_smells}"
    
    return report


def detect_code_smells(code, max_function_length=100, max_long_param_list=5, max_class_size=200):

    tree = ast.parse(code)
    
    smells_summary = {
        'unused_imports': [],
        'long_functions': [],
        'long_param_functions': [],
        'large_classes': []
    }
    
    max_limits = {
        'function_length': max_function_length,
        'param_list': max_long_param_list,
        'class_size': max_class_size
    }

    imports = set()
    used_names = set()
    defined_functions = {}
    defined_classes = {}

    for node in ast.walk(tree):
        # Detect imports////////
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add((alias.name, node.lineno))
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                imports.add((alias.name, node.lineno))

        # Track used names
        if isinstance(node, ast.Name):
            used_names.add(node.id)

        # Detect functions
        if isinstance(node, ast.FunctionDef):
            defined_functions[node.name] = node.lineno
            function_length = node.body[-1].lineno - node.body[0].lineno + 1
            if function_length > max_function_length:
                smells_summary['long_functions'].append((node.name, function_length, node.lineno))

            # Check for long parameter list//////
            if len(node.args.args) > max_long_param_list:
                smells_summary['long_param_functions'].append((node.name, len(node.args.args), node.lineno))

        # Detect classes
        elif isinstance(node, ast.ClassDef):
            defined_classes[node.name] = node.lineno
            class_size = (
                node.body[-1].lineno - node.body[0].lineno + 1 if node.body else 0
            )
            if class_size > max_class_size:
                smells_summary['large_classes'].append((node.name, class_size, node.lineno))

    # Detect unused imports
    for imp, lineno in imports:
        if imp not in used_names:
            smells_summary['unused_imports'].append((imp, lineno))


    # Generate report using the simplified function
    report = generate_report(smells_summary, max_limits)
    return report



@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return 'No file part', 400

    file = request.files['file']
    
    if file.filename == '':
        return 'No selected file', 400

    if file and allowed_file(file.filename):
        if file.filename.endswith('.py'):
            user_code = file.read().decode('utf-8')
            smells_report = detect_code_smells(user_code, max_function_length=100, max_long_param_list=5)
            return render_template('result.html', report=smells_report)
        
        elif file.filename.endswith('.zip'):
            smells_report = process_zip(file)
            return render_template('result.html', report=smells_report)

    return 'Invalid file type. Only .py and .zip files are allowed.', 400

if __name__ == '__main__':
    app.run(debug=True)
