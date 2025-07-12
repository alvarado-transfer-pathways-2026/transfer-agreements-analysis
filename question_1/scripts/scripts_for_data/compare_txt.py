def compare_txt_files(file1, file2):
    with open(file1, 'r') as f1, open(file2, 'r') as f2:
        lines1 = f1.readlines()
        lines2 = f2.readlines()

    if lines1 == lines2:
        print(f"✅ Files '{file1}' and '{file2}' are identical.")
        return True
    else:
        print(f"❌ Files '{file1}' and '{file2}' are different.")
        min_len = min(len(lines1), len(lines2))
        for i in range(min_len):
            if lines1[i] != lines2[i]:
                print(f"First difference at line {i+1}:")
                print(f"{file1}: {lines1[i].rstrip()}")
                print(f"{file2}: {lines2[i].rstrip()}")
                break
        if len(lines1) != len(lines2):
            print(f"Files have different number of lines: {len(lines1)} vs {len(lines2)}")
        return False

if __name__ == "__main__":
    # Replace these with your actual file paths
    file1 = "/Users/yasminkabir/transfer-agreements-analysis/multiorder3average.txt"
    file2 = "/Users/yasminkabir/transfer-agreements-analysis/average_combination_order.txt"
    compare_txt_files(file1, file2)