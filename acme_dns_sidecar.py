def entrypoint(argv):
    print(argv)
    return 0


if __name__ == "__main__":
    import sys
    ret = entrypoint(sys.argv)
    sys.exit(ret)
