from pydub.generators import Sine

@anvil.server.callable
def run_aac_codec_test():
  """
    Performs a self-contained test of the server's ability to encode and decode AAC audio.
    Returns a dictionary with the test results.
    """
  print("--- AAC CODEC DIAGNOSTIC TEST ---")
  try:
    # 1. Generate a 1-second 440Hz sine wave as a known audio source.
    print("[TEST] Step 1: Generating a 1-second test tone...")
    original_tone = Sine(440).to_audio_segment(duration=1000) # 1000 ms = 1 second
    original_duration = len(original_tone)
    print(f"[TEST]   -> Original tone created with duration: {original_duration} ms")

    # 2. Export (encode) this tone to an in-memory MP4 file with the AAC codec.
    print("[TEST] Step 2: Encoding the tone to AAC in an in-memory MP4 container...")
    buffer = io.BytesIO()
    original_tone.export(buffer, format="mp4", codec="aac")
    buffer.seek(0) # Rewind the buffer to the beginning for reading
    buffer_size = len(buffer.getvalue())
    print(f"[TEST]   -> In-memory file created. Size: {buffer_size} bytes.")

    # 3. Import (decode) the audio back from the in-memory buffer. This is the critical test.
    print("[TEST] Step 3: Attempting to decode the AAC audio from the buffer...")
    decoded_audio = AudioSegment.from_file(buffer, format="mp4")
    decoded_duration = len(decoded_audio)
    print(f"[TEST]   -> Decoded audio duration: {decoded_duration} ms")

    # 4. Verify the result. A successful decode will have a duration very close to the original.
    print("[TEST] Step 4: Verifying the duration...")
    # We allow a small tolerance (e.g., 100ms) for any minor processing discrepancies.
    if decoded_duration > (original_duration - 100):
      result = {
        "success": True,
        "message": f"SUCCESS: The AAC codec is working correctly. Decoded duration ({decoded_duration}ms) matches original ({original_duration}ms)."
      }
      print(f"[TEST] {result['message']}")
    else:
      result = {
        "success": False,
        "message": f"FAILURE: The AAC codec is NOT working correctly. Decoded duration ({decoded_duration}ms) is significantly shorter than the original ({original_duration}ms)."
      }
      print(f"[TEST] {result['message']}")

    print("--- TEST COMPLETE ---")
    return result

  except Exception as e:
    error_message = f"CRITICAL FAILURE: The test crashed, indicating a severe issue with pydub/FFmpeg. Error: {str(e)}"
    print(f"[TEST] {error_message}")
    print(traceback.format_exc())
    print("--- TEST FAILED ---")
    return {
      "success": False,
      "message": error_message
    }