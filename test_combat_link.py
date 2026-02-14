
from settings import GRUPPO_AROMA

def get_combat_link_test():
    group_id = str(GRUPPO_AROMA)
    if group_id.startswith("-100"):
        group_id = group_id[4:]
    return f"https://t.me/c/{group_id}/1"

if __name__ == "__main__":
    link = get_combat_link_test()
    print(f"GRUPPO_AROMA: {GRUPPO_AROMA}")
    print(f"Generated Link: {link}")
    
    # Expected for TEST_GRUPPO (-1001721979634)
    expected = "https://t.me/c/1721979634/1"
    if link == expected:
        print("✅ Success!")
    else:
        print(f"❌ Failed! Expected {expected}")
